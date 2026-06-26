using System.Collections.Generic;

namespace AutoCADPlugin
{
    public sealed record ActionExecutionRecord(
        string ActionId,
        string ActionType,
        bool Success,
        bool PreviewOnly,
        string Message,
        string? TargetHandle,
        string? ResultHandle,
        List<string>? MatchedHandles = null
    );

    public sealed record ExecutionReport(
        string RequestId,
        bool PreviewOnly,
        List<ActionExecutionRecord> Actions
    );
}