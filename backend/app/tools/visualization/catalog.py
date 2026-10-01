"""Register the six visualization tools on an analysis registry."""

from backend.app.tools.registry import ToolRegistry
from backend.app.tools.visualization.bar_chart import TOOL as BAR
from backend.app.tools.visualization.boxplot import TOOL as BOX
from backend.app.tools.visualization.heatmap import TOOL as HEAT
from backend.app.tools.visualization.histogram import TOOL as HISTOGRAM
from backend.app.tools.visualization.line_chart import TOOL as LINE
from backend.app.tools.visualization.scatter_plot import TOOL as SCATTER

TOOLS = (BAR, LINE, SCATTER, HISTOGRAM, BOX, HEAT)


def register_visualization(registry: ToolRegistry) -> None:
    for tool in TOOLS:
        registry.register(tool)
