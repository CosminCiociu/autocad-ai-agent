using System;
using System.Collections.Generic;

// Placeholder extractor: populate these objects by integrating with AutoCAD's .NET API.

namespace AutoCADPlugin
{
    public record Point2D(double X, double Y);

    public record BlockRef(string Handle, string Name, string Layer, Point2D Position, double RotationDeg, Dictionary<string, string>? Attributes);

    public record TextEntity(string Handle, string Value, string Layer, Point2D Position, double? Height);

    public record LineEntity(string Handle, string Layer, Point2D Start, Point2D End);

    public record PolylineEntity(string Handle, string Layer, bool Closed, List<Point2D> Vertices);

    public static class BlockReader
    {
        // TODO: Replace placeholder logic with AutoCAD API calls (Application.DocumentManager, Transaction, BlockTableRecord, DBObject casts etc.)
        public static object ExtractContext()
        {
            // Return an anonymous object matching shared/schemas/dwg-context.schema.json
            var ctx = new
            {
                schema_version = "1.0.0",
                request_id = Guid.NewGuid().ToString(),
                drawing = new { name = "unknown", units = "unitless", coordinate_system = "WCS" },
                blocks = new List<object>(),
                texts = new List<object>(),
                lines = new List<object>(),
                polylines = new List<object>()
            };

            return ctx;
        }
    }
}
