using System;
using System.Collections.Generic;
using Newtonsoft.Json.Linq;

namespace AutoCADPlugin
{
    public static class ActionExecutor
    {
        public static ExecutionReport ExecuteActionPlan(ActionPlan plan, DwgContext context, bool previewOnly = false)
        {
            if (plan == null) throw new ArgumentNullException(nameof(plan));
            if (plan.Actions == null)
            {
                return new ExecutionReport(plan.RequestId, previewOnly, new List<ActionExecutionRecord>());
            }

            Console.WriteLine($"Executing action plan {plan.RequestId} ({plan.Actions.Count} actions)");
            var records = new List<ActionExecutionRecord>();
            foreach (var action in plan.Actions)
            {
                Console.WriteLine($"Action {action.Id}: type={action.Type}");
                records.Add(previewOnly ? BuildPreviewRecord(action) : ExecuteAction(action, context));
            }

            return new ExecutionReport(plan.RequestId, previewOnly, records);
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
            // TODO: Use AutoCAD API to insert block reference at the requested position.
            return new ActionExecutionRecord(action.Id, action.Type, true, false, message, null, null);
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

            // TODO: Use AutoCAD API to create a polyline with these vertices.
            return new ActionExecutionRecord(action.Id, action.Type, true, false, message, null, null);
        }

        private static ActionExecutionRecord ExecuteUpdateAttribute(ActionItem action, DwgContext context)
        {
            var args = action.Args;
            var targetHandle = GetString(args, "target_handle");
            var tag = GetString(args, "tag");
            var value = GetString(args, "value");

            var message = $"[EXECUTE] update_attribute target_handle={targetHandle} tag={tag} value={value}";
            Console.WriteLine(message);
            // TODO: Use AutoCAD API to update block attribute values by handle/tag.
            return new ActionExecutionRecord(action.Id, action.Type, true, false, message, targetHandle, null);
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
    }
}
