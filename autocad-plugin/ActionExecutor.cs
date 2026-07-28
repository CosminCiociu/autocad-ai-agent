using System;
using System.Collections.Generic;
using System.Linq;
using Autodesk.AutoCAD.DatabaseServices;
using Autodesk.AutoCAD.Geometry;
using Newtonsoft.Json.Linq;
using AcApplication = Autodesk.AutoCAD.ApplicationServices.Application;

namespace AutoCADPlugin
{
    public static class ActionExecutor
    {
        public static ExecutionReport ExecuteActionPlan(ActionPlan plan, DwgContext context, bool previewOnly = false)
        {
            if (plan == null) throw new ArgumentNullException(nameof(plan));
            if (plan.Actions == null)
            {
                return new ExecutionReport(
                    plan.RequestId,
                    previewOnly,
                    new List<ActionExecutionRecord>(),
                    "done",
                    new List<string>(),
                    new List<TaskNodeExecutionRecord>(),
                    null,
                    new List<GoalSubgoalExecutionRecord>()
                );
            }

            Console.WriteLine($"Executing action plan {plan.RequestId} ({plan.Actions.Count} actions)");
            var records = new List<ActionExecutionRecord>();
            var graph = plan.TaskGraph;
            if (graph == null || graph.Nodes == null || graph.Nodes.Count == 0)
            {
                foreach (var action in plan.Actions)
                {
                    Console.WriteLine($"Action {action.Id}: type={action.Type}");
                    records.Add(previewOnly ? BuildPreviewRecord(action) : ExecuteAction(action, context));
                }

                var linearOverallStatus = records.Any(r => !r.Success) ? "failed" : "done";
                return new ExecutionReport(
                    plan.RequestId,
                    previewOnly,
                    records,
                    linearOverallStatus,
                    records.Select(r => r.ActionId).ToList(),
                    new List<TaskNodeExecutionRecord>(),
                    null,
                    new List<GoalSubgoalExecutionRecord>()
                );
            }

            var actionById = plan.Actions
                .Where(a => a != null && !string.IsNullOrWhiteSpace(a.Id))
                .GroupBy(a => a.Id)
                .ToDictionary(g => g.Key, g => g.First(), StringComparer.OrdinalIgnoreCase);

            var nodeById = graph.Nodes
                .Where(n => n != null && !string.IsNullOrWhiteSpace(n.Id))
                .GroupBy(n => n.Id)
                .ToDictionary(g => g.Key, g => g.First(), StringComparer.OrdinalIgnoreCase);

            var runtimeByNodeId = new Dictionary<string, NodeRuntime>(StringComparer.OrdinalIgnoreCase);
            foreach (var node in graph.Nodes.Where(n => n != null && !string.IsNullOrWhiteSpace(n.Id)))
            {
                runtimeByNodeId[node.Id] = new NodeRuntime(node);
            }

            var executionOrder = ResolveExecutionOrder(graph, nodeById);
            var overallStatus = "done";

            foreach (var nodeId in executionOrder)
            {
                if (!runtimeByNodeId.TryGetValue(nodeId, out var runtime))
                {
                    continue;
                }

                var blockedByFailedDependency = runtime.Node.DependsOn.Any(depId =>
                    runtimeByNodeId.TryGetValue(depId, out var depRuntime) &&
                    string.Equals(depRuntime.Status, "failed", StringComparison.OrdinalIgnoreCase));

                if (blockedByFailedDependency)
                {
                    runtime.Message = "Skipped because a dependency failed.";
                    continue;
                }

                runtime.SetRunning();

                if (!string.Equals(runtime.Node.Kind, "action", StringComparison.OrdinalIgnoreCase))
                {
                    runtime.SetDone($"Node kind '{runtime.Node.Kind}' completed without CAD action.");
                    continue;
                }

                var actionId = runtime.Node.ActionId;
                if (string.IsNullOrWhiteSpace(actionId))
                {
                    runtime.SetFailed("Action node does not map to a valid action_id.");
                    overallStatus = "failed";
                    continue;
                }

                if (!actionById.TryGetValue(actionId!, out var action))
                {
                    runtime.SetFailed("Action node does not map to a valid action_id.");
                    overallStatus = "failed";
                    continue;
                }

                Console.WriteLine($"Task node {runtime.Node.Id}: executing action {action.Id} ({action.Type})");
                var record = previewOnly ? BuildPreviewRecord(action) : ExecuteAction(action, context);
                records.Add(record);

                if (record.Success)
                {
                    runtime.SetDone(record.Message);
                }
                else
                {
                    runtime.SetFailed(record.Message);
                    overallStatus = "failed";
                }
            }

            var nodeResults = executionOrder
                .Where(nodeId => runtimeByNodeId.ContainsKey(nodeId))
                .Select(nodeId => runtimeByNodeId[nodeId].ToRecord(actionById))
                .ToList();

            var goalProgress = BuildGoalProgress(plan, nodeResults);

            return new ExecutionReport(
                plan.RequestId,
                previewOnly,
                records,
                overallStatus,
                executionOrder,
                nodeResults,
                goalProgress.goalStatus,
                goalProgress.subgoalResults
            );
        }

        private static (string? goalStatus, List<GoalSubgoalExecutionRecord> subgoalResults) BuildGoalProgress(
            ActionPlan plan,
            List<TaskNodeExecutionRecord> nodeResults)
        {
            var goalPlan = plan.GoalPlan;
            if (goalPlan == null || goalPlan.Subgoals == null || goalPlan.Subgoals.Count == 0)
            {
                return (null, new List<GoalSubgoalExecutionRecord>());
            }

            var nodeByActionId = nodeResults
                .Where(n => !string.IsNullOrWhiteSpace(n.ActionId))
                .GroupBy(n => n.ActionId!, StringComparer.OrdinalIgnoreCase)
                .ToDictionary(g => g.Key, g => g.First(), StringComparer.OrdinalIgnoreCase);

            var nodeByKind = nodeResults
                .GroupBy(n => n.NodeKind ?? string.Empty, StringComparer.OrdinalIgnoreCase)
                .ToDictionary(g => g.Key, g => g.First(), StringComparer.OrdinalIgnoreCase);

            var subgoalResults = new List<GoalSubgoalExecutionRecord>();
            foreach (var subgoal in goalPlan.Subgoals)
            {
                var mappedStatus = "pending";
                var mappedMessage = "No runtime node mapped for this subgoal.";

                var subgoalActionId = subgoal.ActionId;
                if (!string.IsNullOrWhiteSpace(subgoalActionId) && nodeByActionId.TryGetValue(subgoalActionId!, out var actionNode))
                {
                    mappedStatus = actionNode.Status;
                    mappedMessage = actionNode.Message;
                }
                else
                {
                    var kindKey = subgoal.Kind ?? string.Empty;
                    if (nodeByKind.TryGetValue(kindKey, out var kindNode))
                    {
                        mappedStatus = kindNode.Status;
                        mappedMessage = kindNode.Message;
                    }
                }

                subgoalResults.Add(
                    new GoalSubgoalExecutionRecord(
                        subgoal.Id,
                        subgoal.Title,
                        subgoal.Kind ?? string.Empty,
                        mappedStatus,
                        mappedMessage,
                        subgoal.ActionId
                    )
                );
            }

            string goalStatus;
            if (subgoalResults.Any(s => string.Equals(s.Status, "failed", StringComparison.OrdinalIgnoreCase)))
            {
                goalStatus = "failed";
            }
            else if (subgoalResults.All(s => string.Equals(s.Status, "done", StringComparison.OrdinalIgnoreCase)))
            {
                goalStatus = "done";
            }
            else if (subgoalResults.Any(s => string.Equals(s.Status, "running", StringComparison.OrdinalIgnoreCase)))
            {
                goalStatus = "running";
            }
            else
            {
                goalStatus = "pending";
            }

            return (goalStatus, subgoalResults);
        }

        private static List<string> ResolveExecutionOrder(
            TaskGraph graph,
            Dictionary<string, TaskNode> nodeById)
        {
            if (graph.ExecutionOrder != null && graph.ExecutionOrder.Count > 0)
            {
                return graph.ExecutionOrder
                    .Where(nodeId => !string.IsNullOrWhiteSpace(nodeId))
                    .Select(nodeId => nodeId.Trim())
                    .Where(nodeId => nodeById.ContainsKey(nodeId))
                    .ToList();
            }

            return graph.Nodes
                .Where(node => node != null && !string.IsNullOrWhiteSpace(node.Id))
                .Select(node => node.Id)
                .ToList();
        }

        private sealed class NodeRuntime
        {
            public NodeRuntime(TaskNode node)
            {
                Node = node;
                Status = "pending";
                StatusHistory = new List<string> { "pending" };
                Message = "Node not started.";
            }

            public TaskNode Node { get; }

            public string Status { get; private set; }

            public List<string> StatusHistory { get; }

            public string Message { get; set; }

            public void SetRunning()
            {
                if (!string.Equals(Status, "running", StringComparison.OrdinalIgnoreCase))
                {
                    Status = "running";
                    StatusHistory.Add("running");
                }
            }

            public void SetDone(string message)
            {
                Status = "done";
                StatusHistory.Add("done");
                Message = message;
            }

            public void SetFailed(string message)
            {
                Status = "failed";
                StatusHistory.Add("failed");
                Message = message;
            }

            public TaskNodeExecutionRecord ToRecord(Dictionary<string, ActionItem> actionById)
            {
                string? actionType = null;
                var actionId = Node.ActionId;
                if (!string.IsNullOrWhiteSpace(actionId) && actionById.TryGetValue(actionId!, out var action))
                {
                    actionType = action.Type;
                }

                return new TaskNodeExecutionRecord(
                    Node.Id,
                    Node.Title,
                    Node.Kind,
                    Status,
                    new List<string>(StatusHistory),
                    Node.ActionId,
                    actionType,
                    Node.DependsOn ?? new List<string>(),
                    Message
                );
            }
        }

        private static ActionExecutionRecord BuildPreviewRecord(ActionItem action)
        {
            var message = $"Preview only: {action.Type} not executed.";
            Console.WriteLine($"[PREVIEW] {message}");
            return new ActionExecutionRecord(action.Id, action.Type, true, true, message, null, null);
        }

        private static ActionExecutionRecord ExecuteAction(ActionItem action, DwgContext context)
        {
            switch (action.Type)
            {
                case "insert_block":
                    return ExecuteInsertBlock(action, context);
                case "create_polyline":
                    return ExecuteCreatePolyline(action, context);
                case "update_attribute":
                    return ExecuteUpdateAttribute(action, context);
                case "find_entities":
                    return ExecuteFindEntities(action, context);
                default:
                    {
                        var message = $"Unknown action type: {action.Type}";
                        Console.Error.WriteLine(message);
                        return new ActionExecutionRecord(action.Id, action.Type, false, false, message, null, null);
                    }
            }
        }

        private static ActionExecutionRecord ExecuteInsertBlock(ActionItem action, DwgContext context)
        {
            var args = action.Args;
            var name = GetString(args, "name");
            var layer = GetString(args, "layer");
            var rotation = GetDouble(args, "rotation_deg", 0.0);
            var position = GetPoint(args, "position");
            var scale = GetDouble(args, "scale", 1.0);

            var message = $"[EXECUTE] insert_block name={name} layer={layer} position=({position.X},{position.Y}) rotation={rotation} scale={scale}";
            Console.WriteLine(message);

            if (string.IsNullOrWhiteSpace(name))
            {
                return new ActionExecutionRecord(action.Id, action.Type, false, false, "insert_block failed: missing block name.", null, null);
            }

            var doc = AcApplication.DocumentManager.MdiActiveDocument;
            if (doc == null)
            {
                return new ActionExecutionRecord(action.Id, action.Type, false, false, "insert_block failed: no active AutoCAD document.", null, null);
            }

            try
            {
                using (doc.LockDocument())
                {
                    var db = doc.Database;
                    using (var tr = db.TransactionManager.StartTransaction())
                    {
                        var bt = (BlockTable)tr.GetObject(db.BlockTableId, OpenMode.ForRead);
                        if (!bt.Has(name))
                        {
                            return new ActionExecutionRecord(action.Id, action.Type, false, false, $"insert_block failed: block '{name}' not found.", null, null);
                        }

                        var blockDefId = bt[name];
                        var ms = (BlockTableRecord)tr.GetObject(bt[BlockTableRecord.ModelSpace], OpenMode.ForWrite);
                        var blockRef = new BlockReference(new Point3d(position.X, position.Y, 0.0), blockDefId)
                        {
                            Rotation = rotation * (Math.PI / 180.0),
                            ScaleFactors = new Scale3d(scale > 0 ? scale : 1.0),
                        };

                        if (!string.IsNullOrWhiteSpace(layer))
                        {
                            if (!LayerExists(tr, db, layer))
                            {
                                return new ActionExecutionRecord(action.Id, action.Type, false, false, $"insert_block failed: layer '{layer}' not found.", null, null);
                            }
                            blockRef.Layer = layer;
                        }

                        ms.AppendEntity(blockRef);
                        tr.AddNewlyCreatedDBObject(blockRef, true);

                        var blockDef = (BlockTableRecord)tr.GetObject(blockDefId, OpenMode.ForRead);
                        foreach (ObjectId id in blockDef)
                        {
                            var attributeDef = tr.GetObject(id, OpenMode.ForRead) as AttributeDefinition;
                            if (attributeDef == null || attributeDef.Constant)
                            {
                                continue;
                            }

                            var attributeRef = new AttributeReference();
                            attributeRef.SetAttributeFromBlock(attributeDef, blockRef.BlockTransform);
                            attributeRef.Position = attributeDef.Position.TransformBy(blockRef.BlockTransform);
                            blockRef.AttributeCollection.AppendAttribute(attributeRef);
                            tr.AddNewlyCreatedDBObject(attributeRef, true);
                        }

                        tr.Commit();
                        var successMessage = $"insert_block executed: handle={blockRef.Handle} name={name}";
                        return new ActionExecutionRecord(action.Id, action.Type, true, false, successMessage, null, blockRef.Handle.ToString());
                    }
                }
            }
            catch (Exception ex)
            {
                return new ActionExecutionRecord(action.Id, action.Type, false, false, $"insert_block failed: {ex.Message}", null, null);
            }
        }

        private static ActionExecutionRecord ExecuteCreatePolyline(ActionItem action, DwgContext context)
        {
            var args = action.Args;
            var layer = GetString(args, "layer");
            var closed = GetBool(args, "closed", false);
            var vertices = GetVertices(args, "vertices");

            var message = $"[EXECUTE] create_polyline layer={layer} closed={closed} vertices={vertices.Count}";
            Console.WriteLine(message);
            foreach (var vertex in vertices)
            {
                Console.WriteLine($"  vertex=({vertex.X},{vertex.Y})");
            }

            if (vertices.Count < 2)
            {
                return new ActionExecutionRecord(action.Id, action.Type, false, false, "create_polyline failed: at least 2 vertices are required.", null, null);
            }

            var doc = AcApplication.DocumentManager.MdiActiveDocument;
            if (doc == null)
            {
                return new ActionExecutionRecord(action.Id, action.Type, false, false, "create_polyline failed: no active AutoCAD document.", null, null);
            }

            try
            {
                using (doc.LockDocument())
                {
                    var db = doc.Database;
                    using (var tr = db.TransactionManager.StartTransaction())
                    {
                        var bt = (BlockTable)tr.GetObject(db.BlockTableId, OpenMode.ForRead);
                        var ms = (BlockTableRecord)tr.GetObject(bt[BlockTableRecord.ModelSpace], OpenMode.ForWrite);

                        var polyline = new Polyline();
                        for (var i = 0; i < vertices.Count; i++)
                        {
                            polyline.AddVertexAt(i, new Point2d(vertices[i].X, vertices[i].Y), 0, 0, 0);
                        }
                        polyline.Closed = closed;

                        if (!string.IsNullOrWhiteSpace(layer))
                        {
                            if (!LayerExists(tr, db, layer))
                            {
                                return new ActionExecutionRecord(action.Id, action.Type, false, false, $"create_polyline failed: layer '{layer}' not found.", null, null);
                            }
                            polyline.Layer = layer;
                        }

                        ms.AppendEntity(polyline);
                        tr.AddNewlyCreatedDBObject(polyline, true);
                        tr.Commit();

                        var successMessage = $"create_polyline executed: handle={polyline.Handle} vertices={vertices.Count} closed={closed}";
                        return new ActionExecutionRecord(action.Id, action.Type, true, false, successMessage, null, polyline.Handle.ToString());
                    }
                }
            }
            catch (Exception ex)
            {
                return new ActionExecutionRecord(action.Id, action.Type, false, false, $"create_polyline failed: {ex.Message}", null, null);
            }
        }

        private static ActionExecutionRecord ExecuteUpdateAttribute(ActionItem action, DwgContext context)
        {
            var args = action.Args;
            var targetHandle = GetString(args, "target_handle");
            var tag = GetString(args, "tag");
            var value = GetString(args, "value");

            var message = $"[EXECUTE] update_attribute target_handle={targetHandle} tag={tag} value={value}";
            Console.WriteLine(message);

            if (string.IsNullOrWhiteSpace(targetHandle) || string.IsNullOrWhiteSpace(tag))
            {
                return new ActionExecutionRecord(action.Id, action.Type, false, false, "update_attribute failed: target_handle and tag are required.", targetHandle, null);
            }

            var doc = AcApplication.DocumentManager.MdiActiveDocument;
            if (doc == null)
            {
                return new ActionExecutionRecord(action.Id, action.Type, false, false, "update_attribute failed: no active AutoCAD document.", targetHandle, null);
            }

            try
            {
                using (doc.LockDocument())
                {
                    var db = doc.Database;
                    using (var tr = db.TransactionManager.StartTransaction())
                    {
                        if (!TryGetObjectIdByHandle(db, targetHandle, out var entityId))
                        {
                            return new ActionExecutionRecord(action.Id, action.Type, false, false, $"update_attribute failed: handle '{targetHandle}' not found.", targetHandle, null);
                        }

                        var blockRef = tr.GetObject(entityId, OpenMode.ForWrite) as BlockReference;
                        if (blockRef == null)
                        {
                            return new ActionExecutionRecord(action.Id, action.Type, false, false, $"update_attribute failed: entity '{targetHandle}' is not a block reference.", targetHandle, null);
                        }

                        var updated = false;
                        foreach (ObjectId attributeId in blockRef.AttributeCollection)
                        {
                            var attributeRef = tr.GetObject(attributeId, OpenMode.ForWrite) as AttributeReference;
                            if (attributeRef == null)
                            {
                                continue;
                            }

                            if (!string.Equals(attributeRef.Tag, tag, StringComparison.OrdinalIgnoreCase))
                            {
                                continue;
                            }

                            attributeRef.TextString = value;
                            updated = true;
                            break;
                        }

                        if (!updated)
                        {
                            return new ActionExecutionRecord(action.Id, action.Type, false, false, $"update_attribute failed: tag '{tag}' not found on block '{targetHandle}'.", targetHandle, null);
                        }

                        tr.Commit();
                        var successMessage = $"update_attribute executed: target_handle={targetHandle} tag={tag}";
                        return new ActionExecutionRecord(action.Id, action.Type, true, false, successMessage, targetHandle, targetHandle);
                    }
                }
            }
            catch (Exception ex)
            {
                return new ActionExecutionRecord(action.Id, action.Type, false, false, $"update_attribute failed: {ex.Message}", targetHandle, null);
            }
        }

        private static ActionExecutionRecord ExecuteFindEntities(ActionItem action, DwgContext context)
        {
            var args = action.Args;
            var entityType = GetString(args, "entity_type");
            var layer = GetString(args, "layer");
            var name = GetString(args, "name");
            var textContains = GetString(args, "text_contains");

            var matchedHandles = FindMatchingHandles(context, entityType, layer, name, textContains);
            var message = $"[EXECUTE] find_entities type={entityType} layer={layer} name={name} text_contains={textContains} matches={matchedHandles.Count}";
            Console.WriteLine(message);
            if (matchedHandles.Count > 0)
            {
                Console.WriteLine($"  matched_handles={string.Join(",", matchedHandles)}");
            }

            // In AutoCAD 2024 this is the first action we can safely resolve end-to-end
            // without mutating the drawing: it searches the extracted context and can be
            // swapped later with a live selection/highlight implementation.
            return new ActionExecutionRecord(action.Id, action.Type, true, false, message, null, null, matchedHandles);
        }

        private static List<string> FindMatchingHandles(DwgContext context, string entityType, string layer, string name, string textContains)
        {
            var matches = new List<string>();
            var type = (entityType ?? string.Empty).Trim().ToLowerInvariant();

            if (type == "block" || string.IsNullOrEmpty(type))
            {
                foreach (var block in context.Blocks)
                {
                    if (!string.IsNullOrWhiteSpace(layer) && !string.Equals(block.Layer, layer, StringComparison.OrdinalIgnoreCase))
                    {
                        continue;
                    }

                    if (!string.IsNullOrWhiteSpace(name) && !string.Equals(block.Name, name, StringComparison.OrdinalIgnoreCase))
                    {
                        continue;
                    }

                    matches.Add(block.Handle);
                }

                if (!string.IsNullOrEmpty(type))
                {
                    return matches;
                }
            }

            if (type == "text")
            {
                foreach (var text in context.Texts)
                {
                    if (!string.IsNullOrWhiteSpace(layer) && !string.Equals(text.Layer, layer, StringComparison.OrdinalIgnoreCase))
                    {
                        continue;
                    }

                    if (!string.IsNullOrWhiteSpace(textContains) &&
                        text.Value.IndexOf(textContains, StringComparison.OrdinalIgnoreCase) < 0)
                    {
                        continue;
                    }

                    matches.Add(text.Handle);
                }

                return matches;
            }

            if (type == "line")
            {
                foreach (var line in context.Lines)
                {
                    if (!string.IsNullOrWhiteSpace(layer) && !string.Equals(line.Layer, layer, StringComparison.OrdinalIgnoreCase))
                    {
                        continue;
                    }

                    matches.Add(line.Handle);
                }

                return matches;
            }

            if (type == "polyline")
            {
                foreach (var polyline in context.Polylines)
                {
                    if (!string.IsNullOrWhiteSpace(layer) && !string.Equals(polyline.Layer, layer, StringComparison.OrdinalIgnoreCase))
                    {
                        continue;
                    }

                    matches.Add(polyline.Handle);
                }

                return matches;
            }

            return matches;
        }

        private static Point2D GetPoint(JObject args, string propertyName)
        {
            if (args.TryGetValue(propertyName, out var token) && token is JObject pointObj)
            {
                var x = GetDouble(pointObj, "x", 0.0);
                var y = GetDouble(pointObj, "y", 0.0);
                return new Point2D(x, y);
            }

            return new Point2D(0, 0);
        }

        private static List<Point2D> GetVertices(JObject args, string propertyName)
        {
            var vertices = new List<Point2D>();
            if (args.TryGetValue(propertyName, out var token) && token is JArray array)
            {
                foreach (var item in array)
                {
                    if (item is JObject pointObj)
                    {
                        var x = GetDouble(pointObj, "x", 0.0);
                        var y = GetDouble(pointObj, "y", 0.0);
                        vertices.Add(new Point2D(x, y));
                    }
                }
            }

            return vertices;
        }

        private static string GetString(JObject args, string propertyName)
        {
            if (args.TryGetValue(propertyName, out var token) && token.Type == JTokenType.String)
            {
                return token.Value<string>() ?? string.Empty;
            }

            return string.Empty;
        }

        private static double GetDouble(JObject args, string propertyName, double defaultValue)
        {
            if (args.TryGetValue(propertyName, out var token) && (token.Type == JTokenType.Float || token.Type == JTokenType.Integer))
            {
                return token.Value<double>();
            }

            return defaultValue;
        }

        private static bool GetBool(JObject args, string propertyName, bool defaultValue)
        {
            if (args.TryGetValue(propertyName, out var token) && token.Type == JTokenType.Boolean)
            {
                return token.Value<bool>();
            }

            return defaultValue;
        }

        private static bool LayerExists(Transaction tr, Database db, string layerName)
        {
            if (string.IsNullOrWhiteSpace(layerName))
            {
                return false;
            }

            var lt = (LayerTable)tr.GetObject(db.LayerTableId, OpenMode.ForRead);
            return lt.Has(layerName);
        }

        private static bool TryGetObjectIdByHandle(Database db, string handleText, out ObjectId objectId)
        {
            objectId = ObjectId.Null;
            if (string.IsNullOrWhiteSpace(handleText))
            {
                return false;
            }

            try
            {
                var handleValue = Convert.ToInt64(handleText, 16);
                var handle = new Handle(handleValue);
                objectId = db.GetObjectId(false, handle, 0);
                return !objectId.IsNull;
            }
            catch
            {
                return false;
            }
        }
    }
}
