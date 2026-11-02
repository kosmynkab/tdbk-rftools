"""Independent tools registered in the TDBK RFTools palette."""


def get_tool_classes():
    # Keep RoboFont imports out of the pure calculation/test boundary.
    from .contour_probe import ContourProbeTool
    from .distribute_points import DistributePointsTool
    from .selected_points import SelectedPointsTool
    from .cleanup import CleanupTool

    return (SelectedPointsTool, ContourProbeTool, DistributePointsTool, CleanupTool)


__all__ = ("get_tool_classes",)
