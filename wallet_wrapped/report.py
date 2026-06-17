"""The terminal view of a :class:`~wallet_wrapped.wrapped.Wrapped`.

Same data as the SVG card, rendered with ``rich`` for the console.
"""

from __future__ import annotations

from rich.align import Align
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .wrapped import Wrapped, money

_BAR_WIDTH = 56


def _ring_style(score: int) -> str:
    if score >= 67:
        return "bold green"
    if score >= 34:
        return "bold yellow"
    return "bold red"


def _allocation_bar(w: Wrapped) -> Text:
    bar = Text()
    if not w.allocation:
        return Text("  (no holdings)", style="dim")
    total = sum(a.pct for a in w.allocation) or 100.0
    used = 0
    for i, a in enumerate(w.allocation):
        cells = round(_BAR_WIDTH * a.pct / total)
        if i == len(w.allocation) - 1:
            cells = max(0, _BAR_WIDTH - used)  # absorb rounding into the last slice
        used += cells
        bar.append("█" * cells, style=a.color)
    return bar


def _legend(w: Wrapped) -> Text:
    legend = Text()
    for i, a in enumerate(w.allocation):
        if i:
            legend.append("   ")
        legend.append("● ", style=a.color)
        legend.append(f"{a.label} ", style="white")
        legend.append(f"{a.pct:.0f}%", style="dim")
    return legend


def build_report(w: Wrapped, generated_at: str = "") -> Panel:
    """Build the renderable panel for ``w``."""
    rows = []

    # net worth + persona
    nw = Text()
    nw.append("  Net worth  ", style="dim")
    nw.append(money(w.net_worth), style="bold cyan")
    rows.append(nw)

    persona = Text("  ")
    persona.append(f"{w.persona.emoji} {w.persona.name}", style="bold magenta")
    persona.append(f"  — {w.persona.tagline}", style="italic dim")
    rows.append(persona)
    rows.append(Text(""))

    # stat line
    stats = Text("  ")
    for value, label in (
        (str(w.n_chains), "chains"),
        (str(w.n_tokens), "tokens"),
        (str(w.n_protocols), "protocols"),
        (f"{w.defi_ratio * 100:.0f}%", "in DeFi"),
    ):
        stats.append(f"{value} ", style="bold white")
        stats.append(f"{label}    ", style="dim")
    rows.append(stats)

    # diversification gauge
    filled = round(_BAR_WIDTH * w.diversification / 100)
    gauge = Text("  Diversification  ")
    gauge.append("█" * filled, style=_ring_style(w.diversification))
    gauge.append("░" * (_BAR_WIDTH - filled), style="grey30")
    gauge.append(f"  {w.diversification}/100", style=_ring_style(w.diversification))
    rows.append(gauge)
    rows.append(Text(""))

    # allocation
    rows.append(Text("  Portfolio allocation", style="dim"))
    rows.append(Text("  ") + _allocation_bar(w))
    rows.append(Text("  ") + _legend(w))
    rows.append(Text(""))

    # top tokens + protocols, side by side
    rows.append(_two_tables(w))

    # fun facts
    if w.fun_facts:
        rows.append(Text(""))
        for fact in w.fun_facts:
            rows.append(Text(f"  • {fact}", style="dim"))

    subtitle = "data: CoinStats Crypto API · /wallet/balance + /wallet/defi"
    if generated_at:
        subtitle = f"as of {generated_at} · " + subtitle

    return Panel(
        Group(*rows),
        title=f"[bold]🎁 WALLET WRAPPED[/]  ·  [cyan]{w.short_address}[/]",
        subtitle=f"[dim]{subtitle}[/]",
        border_style="cyan",
        padding=(1, 2),
    )


def _two_tables(w: Wrapped):
    tokens = Table(
        title="Top tokens", title_style="dim", box=None, pad_edge=False, expand=True
    )
    tokens.add_column("Token", style="white")
    tokens.add_column("Value", justify="right", style="cyan")
    tokens.add_column("%", justify="right", style="dim")
    if w.top_tokens:
        for t in w.top_tokens:
            tokens.add_row(t.label, money(t.value_usd), f"{t.pct:.0f}%")
    else:
        tokens.add_row("—", "", "")

    protos = Table(
        title="Top DeFi protocols",
        title_style="dim",
        box=None,
        pad_edge=False,
        expand=True,
    )
    protos.add_column("Protocol", style="white")
    protos.add_column("Value", justify="right", style="green")
    protos.add_column("Type", style="dim")
    if w.top_protocols:
        for p in w.top_protocols:
            protos.add_row(p.name, money(p.value_usd), ", ".join(p.kinds) or "—")
    else:
        protos.add_row("—", "", "")

    grid = Table.grid(expand=True, padding=(0, 2))
    grid.add_column(ratio=1)
    grid.add_column(ratio=1)
    grid.add_row(tokens, protos)
    return Align.left(grid)


def print_report(w: Wrapped, generated_at: str = "", console: Console = None) -> None:
    console = console or Console()
    console.print(build_report(w, generated_at))
