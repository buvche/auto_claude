#!/usr/bin/env python3
"""
Envision - Codebase Improvement Analyzer

Analyzes the codebase and proposes small, focused improvements when there's
nothing else to do. Uses Claude to identify opportunities for code quality
improvements, missing tests, documentation gaps, and potential bugs.
"""

import argparse
import asyncio
import json
import time
from dataclasses import dataclass
from pathlib import Path

from claude_code_sdk import ClaudeCodeOptions, query

# Configuration
PROJECT_DIR = Path(__file__).parent.resolve()
IGNORE_PATTERNS = {".git", "__pycache__", "venv", ".venv", "node_modules", ".pyc", ".pyo"}

# Analysis categories
ANALYSIS_CATEGORIES = [
    "code_quality",
    "missing_tests",
    "documentation_gaps",
    "potential_bugs",
]


@dataclass
class Improvement:
    """Represents a proposed improvement."""
    category: str
    title: str
    description: str
    file_path: str | None
    estimated_time_minutes: int
    priority: str  # "low", "medium", "high"


@dataclass
class UsageStats:
    """Claude API usage statistics."""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    total_cost_usd: float = 0.0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def estimate_cost(self) -> float:
        """Estimate cost based on token usage (Sonnet 3.5 pricing)."""
        if self.total_cost_usd > 0:
            return self.total_cost_usd
        # Sonnet pricing: $3/M input, $15/M output, $0.30/M cache read
        input_cost = self.input_tokens * 0.000003
        output_cost = self.output_tokens * 0.000015
        cache_cost = self.cache_read_tokens * 0.0000003
        return input_cost + output_cost + cache_cost


@dataclass
class EnvisionResult:
    """Result of the envision analysis."""
    improvements: list[Improvement]
    analysis_time_seconds: float
    files_analyzed: int
    usage: UsageStats | None = None


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Analyze codebase and propose improvements",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python envision.py                      # Run with defaults
  python envision.py --max-agents 5       # Use up to 5 parallel agents
  python envision.py --max-time 300       # Limit analysis to 5 minutes
  python envision.py --output json        # Output as JSON
        """
    )
    parser.add_argument(
        "--max-agents",
        type=int,
        default=3,
        help="Maximum number of parallel analysis agents (default: 3)"
    )
    parser.add_argument(
        "--max-time",
        type=int,
        default=600,
        help="Maximum time in seconds for analysis (default: 600)"
    )
    parser.add_argument(
        "--output",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)"
    )
    parser.add_argument(
        "--category",
        choices=ANALYSIS_CATEGORIES + ["all"],
        default="all",
        help="Category to analyze (default: all)"
    )
    return parser.parse_args()


def build_analysis_prompt() -> str:
    """Build the prompt for codebase analysis."""
    return """You are a code improvement analyst. Analyze this codebase to find opportunities for improvement.

IMPORTANT: This is a READ-ONLY analysis. DO NOT make any changes. Only identify and report improvements.

Focus on these categories:
1. **Code Quality**: Refactoring opportunities, code smells, complexity issues
2. **Missing Tests**: Functions/modules without adequate test coverage
3. **Documentation Gaps**: Missing docstrings, unclear code, outdated comments
4. **Potential Bugs**: Error handling issues, edge cases, security concerns

For each improvement you identify:
- Keep it small and focused (max 10 minutes of work)
- Be specific about the file and location
- Explain WHY it's an improvement
- Estimate time to implement

Start by exploring the codebase structure using Glob, then Read key files to understand the code.

Output your findings in this exact format (one improvement per block):

---IMPROVEMENT---
CATEGORY: <one of: code_quality, missing_tests, documentation_gaps, potential_bugs>
TITLE: <short descriptive title>
FILE: <file path or "N/A" if general>
PRIORITY: <low, medium, or high>
TIME_ESTIMATE: <number of minutes>
DESCRIPTION: <detailed description of the improvement>
---END---

Find 3-5 high-value improvements. Focus on practical, actionable items."""


def parse_improvements_from_response(response_text: str) -> list[Improvement]:
    """Parse improvement blocks from Claude's response."""
    improvements: list[Improvement] = []

    # Split by improvement markers
    blocks = response_text.split("---IMPROVEMENT---")

    for block in blocks[1:]:  # Skip the first split (before first marker)
        if "---END---" not in block:
            continue

        content = block.split("---END---")[0].strip()

        # Parse fields
        lines = content.split("\n")
        improvement_data: dict[str, str] = {}
        current_field = ""
        current_value: list[str] = []

        for line in lines:
            if line.startswith("CATEGORY:"):
                if current_field:
                    improvement_data[current_field] = "\n".join(current_value).strip()
                current_field = "category"
                current_value = [line.replace("CATEGORY:", "").strip()]
            elif line.startswith("TITLE:"):
                if current_field:
                    improvement_data[current_field] = "\n".join(current_value).strip()
                current_field = "title"
                current_value = [line.replace("TITLE:", "").strip()]
            elif line.startswith("FILE:"):
                if current_field:
                    improvement_data[current_field] = "\n".join(current_value).strip()
                current_field = "file_path"
                current_value = [line.replace("FILE:", "").strip()]
            elif line.startswith("PRIORITY:"):
                if current_field:
                    improvement_data[current_field] = "\n".join(current_value).strip()
                current_field = "priority"
                current_value = [line.replace("PRIORITY:", "").strip()]
            elif line.startswith("TIME_ESTIMATE:"):
                if current_field:
                    improvement_data[current_field] = "\n".join(current_value).strip()
                current_field = "time_estimate"
                current_value = [line.replace("TIME_ESTIMATE:", "").strip()]
            elif line.startswith("DESCRIPTION:"):
                if current_field:
                    improvement_data[current_field] = "\n".join(current_value).strip()
                current_field = "description"
                current_value = [line.replace("DESCRIPTION:", "").strip()]
            else:
                current_value.append(line)

        # Don't forget the last field
        if current_field:
            improvement_data[current_field] = "\n".join(current_value).strip()

        # Create improvement object if we have required fields
        if all(k in improvement_data for k in ["category", "title", "description"]):
            # Parse time estimate
            time_str = improvement_data.get("time_estimate", "10")
            try:
                time_minutes = int("".join(c for c in time_str if c.isdigit()) or "10")
            except ValueError:
                time_minutes = 10

            file_path = improvement_data.get("file_path", "N/A")
            if file_path.upper() == "N/A":
                file_path = None

            improvements.append(Improvement(
                category=improvement_data["category"].lower().replace(" ", "_"),
                title=improvement_data["title"],
                description=improvement_data["description"],
                file_path=file_path,
                estimated_time_minutes=min(time_minutes, 10),  # Cap at 10 min
                priority=improvement_data.get("priority", "medium").lower(),
            ))

    return improvements


async def run_analysis(max_time: int) -> tuple[str, int, UsageStats]:
    """Run the Claude analysis and return the response text, file count, and usage stats."""
    prompt = build_analysis_prompt()

    options = ClaudeCodeOptions(
        allowed_tools=["Read", "Glob", "Grep"],  # Read-only tools only
        cwd=str(PROJECT_DIR),
        max_turns=20,  # Limit conversation turns
    )

    result_text = ""
    files_analyzed = 0
    start_time = time.time()

    # Track usage from messages
    usage = UsageStats()
    processed_message_ids: set[str] = set()

    async for message in query(prompt=prompt, options=options):
        # Check time limit
        if time.time() - start_time > max_time:
            break

        # Track usage from assistant messages (deduplicate by message ID)
        message_id = getattr(message, "id", None)
        if message_id and message_id not in processed_message_ids:
            msg_usage = getattr(message, "usage", None)
            if msg_usage:
                processed_message_ids.add(message_id)
                # Extract usage data (handle both dict and object)
                if isinstance(msg_usage, dict):
                    usage.input_tokens += msg_usage.get("input_tokens", 0)
                    usage.output_tokens += msg_usage.get("output_tokens", 0)
                    usage.cache_read_tokens += msg_usage.get("cache_read_input_tokens", 0)
                    usage.cache_creation_tokens += msg_usage.get("cache_creation_input_tokens", 0)
                else:
                    usage.input_tokens += getattr(msg_usage, "input_tokens", 0)
                    usage.output_tokens += getattr(msg_usage, "output_tokens", 0)
                    usage.cache_read_tokens += getattr(msg_usage, "cache_read_input_tokens", 0)
                    usage.cache_creation_tokens += getattr(msg_usage, "cache_creation_input_tokens", 0)

        # Check for final result with total cost
        if hasattr(message, "total_cost_usd") and message.total_cost_usd:
            usage.total_cost_usd = float(message.total_cost_usd)

        if hasattr(message, "content"):
            if isinstance(message.content, str):
                result_text += message.content
            elif isinstance(message.content, list):
                for block in message.content:
                    if hasattr(block, "text"):
                        result_text += block.text
                    # Count tool uses for file reading
                    if hasattr(block, "name") and block.name in ("Read", "Glob"):
                        files_analyzed += 1
        elif hasattr(message, "result") and message.result:
            result_text = str(message.result)

    return result_text, max(files_analyzed, 1), usage


async def analyze_codebase(max_agents: int, max_time: int, category: str) -> EnvisionResult:
    """Analyze the codebase for improvement opportunities."""
    start_time = time.time()

    # For now, run single analysis (parallel agents can be added later)
    # max_agents is available for future parallel category analysis
    response_text, files_analyzed, usage = await run_analysis(max_time)

    # Parse improvements from response
    improvements = parse_improvements_from_response(response_text)

    # Filter by category if specified
    if category != "all":
        improvements = [i for i in improvements if i.category == category]

    # Sort by priority (high > medium > low)
    priority_order = {"high": 0, "medium": 1, "low": 2}
    improvements.sort(key=lambda x: priority_order.get(x.priority, 1))

    analysis_time = time.time() - start_time

    return EnvisionResult(
        improvements=improvements,
        analysis_time_seconds=round(analysis_time, 2),
        files_analyzed=files_analyzed,
        usage=usage,
    )


def format_output_text(result: EnvisionResult) -> str:
    """Format the result as human-readable text."""
    lines = [
        "",
        "=" * 60,
        "  CODEBASE IMPROVEMENT PROPOSALS",
        "=" * 60,
        "",
        f"Analysis completed in {result.analysis_time_seconds:.1f}s",
        f"Files analyzed: {result.files_analyzed}",
        f"Improvements found: {len(result.improvements)}",
    ]

    # Add usage stats if available
    if result.usage:
        lines.extend([
            "",
            "-" * 60,
            "  API USAGE",
            "-" * 60,
            f"  Input tokens:  {result.usage.input_tokens:,}",
            f"  Output tokens: {result.usage.output_tokens:,}",
            f"  Total tokens:  {result.usage.total_tokens:,}",
        ])
        if result.usage.cache_read_tokens > 0:
            lines.append(f"  Cache read:    {result.usage.cache_read_tokens:,}")
        cost = result.usage.estimate_cost()
        lines.append(f"  Est. cost:     ${cost:.4f}")
        lines.append("-" * 60)

    lines.append("")

    if not result.improvements:
        lines.append("No improvements identified. The codebase looks good!")
    else:
        for i, improvement in enumerate(result.improvements, 1):
            priority_icon = {"high": "[!]", "medium": "[*]", "low": "[-]"}.get(
                improvement.priority, "[*]"
            )
            lines.extend([
                "-" * 60,
                f"{priority_icon} {i}. {improvement.title}",
                f"   Category: {improvement.category.replace('_', ' ').title()}",
                f"   Priority: {improvement.priority.upper()}",
                f"   Estimated time: ~{improvement.estimated_time_minutes} min",
            ])
            if improvement.file_path:
                lines.append(f"   File: {improvement.file_path}")
            lines.extend([
                "",
                f"   {improvement.description}",
                "",
            ])

    lines.extend([
        "=" * 60,
        "NOTE: These are proposals only. No changes have been made.",
        "=" * 60,
        "",
    ])

    return "\n".join(lines)


def format_output_json(result: EnvisionResult) -> str:
    """Format the result as JSON."""
    data = {
        "analysis_time_seconds": result.analysis_time_seconds,
        "files_analyzed": result.files_analyzed,
        "improvements_count": len(result.improvements),
        "improvements": [
            {
                "category": i.category,
                "title": i.title,
                "description": i.description,
                "file_path": i.file_path,
                "estimated_time_minutes": i.estimated_time_minutes,
                "priority": i.priority,
            }
            for i in result.improvements
        ],
    }
    # Add usage if available
    if result.usage:
        data["usage"] = {
            "input_tokens": result.usage.input_tokens,
            "output_tokens": result.usage.output_tokens,
            "total_tokens": result.usage.total_tokens,
            "cache_read_tokens": result.usage.cache_read_tokens,
            "estimated_cost_usd": result.usage.estimate_cost(),
        }
    return json.dumps(data, indent=2)


def write_github_summary(result: EnvisionResult) -> None:
    """Write summary to GitHub Actions step summary if available."""
    import os
    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_file:
        return

    lines = [
        "## Envision Analysis Results",
        "",
        f"**Analysis Time:** {result.analysis_time_seconds:.1f}s",
        f"**Files Analyzed:** {result.files_analyzed}",
        f"**Improvements Found:** {len(result.improvements)}",
        "",
    ]

    # Add usage stats
    if result.usage:
        cost = result.usage.estimate_cost()
        lines.extend([
            "### API Usage",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Input tokens | {result.usage.input_tokens:,} |",
            f"| Output tokens | {result.usage.output_tokens:,} |",
            f"| Total tokens | {result.usage.total_tokens:,} |",
            f"| Estimated cost | ${cost:.4f} |",
            "",
        ])

    # Add improvements table
    if result.improvements:
        lines.extend([
            "### Proposed Improvements",
            "",
            "| Priority | Title | Category | Est. Time |",
            "|----------|-------|----------|-----------|",
        ])
        for imp in result.improvements:
            priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(imp.priority, "⚪")
            lines.append(
                f"| {priority_emoji} {imp.priority.upper()} | {imp.title} | "
                f"{imp.category.replace('_', ' ').title()} | ~{imp.estimated_time_minutes} min |"
            )
    else:
        lines.append("✅ No improvements needed - codebase looks good!")

    try:
        with open(summary_file, "a") as f:
            f.write("\n".join(lines) + "\n")
    except OSError:
        pass  # Silently fail if we can't write


async def main() -> None:
    """Main entry point."""
    args = parse_args()

    print("""
+----------------------------------------------------------+
|                    ENVISION                              |
|           Codebase Improvement Analyzer                  |
+----------------------------------------------------------+
    """)

    print(f"Analyzing codebase: {PROJECT_DIR}")
    print(f"Max agents: {args.max_agents}")
    print(f"Max time: {args.max_time}s")
    print(f"Category: {args.category}")
    print("\nStarting analysis (this may take a few minutes)...\n")

    try:
        result = await analyze_codebase(
            max_agents=args.max_agents,
            max_time=args.max_time,
            category=args.category,
        )

        if args.output == "json":
            print(format_output_json(result))
        else:
            print(format_output_text(result))

        # Write GitHub Actions summary if running in CI
        write_github_summary(result)

    except KeyboardInterrupt:
        print("\n\nAnalysis interrupted by user.")
    except Exception as e:
        print(f"\nError during analysis: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
