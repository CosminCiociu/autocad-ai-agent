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

    public record DwgDrawing(string Name, string Units, string CoordinateSystem);

    public record DwgContext(
        string SchemaVersion,
        string RequestId,
        DwgDrawing Drawing,
        List<BlockRef> Blocks,
        List<TextEntity> Texts,
        List<LineEntity> Lines,
        List<PolylineEntity> Polylines
    );

    public static class BlockReader
    {
        // TODO: Replace placeholder logic with AutoCAD API calls.
        // In AutoCAD .NET, use Transaction, BlockTable, BlockTableRecord, BlockReference,
        // DBText/MText, Line, Polyline, and transformation to WCS.
        public static DwgContext ExtractContext()
        {
            var ctx = new DwgContext(
                SchemaVersion: "1.0.0",
                RequestId: Guid.NewGuid().ToString(),
                Drawing: new DwgDrawing(Name: "unknown", Units: "unitless", CoordinateSystem: "WCS"),
                Blocks: new List<BlockRef>(),
                Texts: new List<TextEntity>(),
                Lines: new List<LineEntity>(),
                Polylines: new List<PolylineEntity>()
            );

            return ctx;
        }
    }
}
