using System;
using System.Collections.Generic;
using Newtonsoft.Json;

// Placeholder extractor: populate these objects by integrating with AutoCAD's .NET API.

namespace AutoCADPlugin
{
    public record Point2D(
        [property: JsonProperty("x")] double X,
        [property: JsonProperty("y")] double Y
    );

    public record BlockRef(
        [property: JsonProperty("handle")] string Handle,
        [property: JsonProperty("name")] string Name,
        [property: JsonProperty("layer")] string Layer,
        [property: JsonProperty("position")] Point2D Position,
        [property: JsonProperty("rotation_deg")] double RotationDeg,
        [property: JsonProperty("attributes")] Dictionary<string, string>? Attributes
    );

    public record TextEntity(
        [property: JsonProperty("handle")] string Handle,
        [property: JsonProperty("value")] string Value,
        [property: JsonProperty("layer")] string Layer,
        [property: JsonProperty("position")] Point2D Position,
        [property: JsonProperty("height")] double? Height
    );

    public record LineEntity(
        [property: JsonProperty("handle")] string Handle,
        [property: JsonProperty("layer")] string Layer,
        [property: JsonProperty("start")] Point2D Start,
        [property: JsonProperty("end")] Point2D End
    );

    public record PolylineEntity(
        [property: JsonProperty("handle")] string Handle,
        [property: JsonProperty("layer")] string Layer,
        [property: JsonProperty("closed")] bool Closed,
        [property: JsonProperty("vertices")] List<Point2D> Vertices
    );

    public record DwgDrawing(
        [property: JsonProperty("name")] string Name,
        [property: JsonProperty("units")] string Units,
        [property: JsonProperty("coordinate_system")] string CoordinateSystem
    );

    public record DwgContext(
        [property: JsonProperty("schema_version")] string SchemaVersion,
        [property: JsonProperty("request_id")] string RequestId,
        [property: JsonProperty("drawing")] DwgDrawing Drawing,
        [property: JsonProperty("blocks")] List<BlockRef> Blocks,
        [property: JsonProperty("texts")] List<TextEntity> Texts,
        [property: JsonProperty("lines")] List<LineEntity> Lines,
        [property: JsonProperty("polylines")] List<PolylineEntity> Polylines
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
