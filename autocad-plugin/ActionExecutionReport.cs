using System.Collections.Generic;

namespace AutoCADPlugin
{
    public sealed record GoalSubgoalExecutionRecord(
        string SubgoalId,
        string Title,
        string Kind,
        string Status,
        string Message,
        string? ActionId
    );

    public sealed record TaskNodeExecutionRecord(
        string NodeId,
        string NodeTitle,
        string NodeKind,
        string Status,
        List<string> StatusHistory,
        string? ActionId,
        string? ActionType,
        List<string> DependsOn,
        string Message
    );

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
        List<ActionExecutionRecord> Actions,
        string OverallStatus,
        List<string>? ExecutionOrder = null,
        List<TaskNodeExecutionRecord>? NodeResults = null,
        string? GoalStatus = null,
        List<GoalSubgoalExecutionRecord>? SubgoalResults = null
    );
}