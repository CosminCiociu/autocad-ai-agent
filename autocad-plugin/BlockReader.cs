using System;
using System.Collections.Generic;
using System.Text.RegularExpressions;
using Autodesk.AutoCAD.DatabaseServices;
using Autodesk.AutoCAD.Geometry;
using Autodesk.AutoCAD.Runtime;
using Newtonsoft.Json;
using AcApplication = Autodesk.AutoCAD.ApplicationServices.Application;

namespace AutoCADPlugin
{
    public record Point2D(
        [property: JsonProperty("x")] double X,
        [property: JsonProperty("y")] double Y
    );

    public record BlockAttribute(
        [property: JsonProperty("tag")] string Tag,
        [property: JsonProperty("value")] string Value
    );

    public record BlockRef(
        [property: JsonProperty("handle")] string Handle,
        [property: JsonProperty("name")] string Name,
        [property: JsonProperty("layer")] string Layer,
        [property: JsonProperty("position")] Point2D Position,
        [property: JsonProperty("rotation_deg")] double RotationDeg,
        [property: JsonProperty("scale")] double Scale,
        [property: JsonProperty("color_index")] int ColorIndex,
        [property: JsonProperty("is_dynamic")] bool IsDynamic,
        [property: JsonProperty("description")] string Description,
        [property: JsonProperty("attributes")] List<BlockAttribute> Attributes
    );

    public record TextEntity(
        [property: JsonProperty("handle")] string Handle,
        [property: JsonProperty("value")] string Value,
        [property: JsonProperty("value_plain")] string ValuePlain,
        [property: JsonProperty("layer")] string Layer,
        [property: JsonProperty("position")] Point2D Position,
        [property: JsonProperty("height")] double? Height,
        [property: JsonProperty("style")] string Style,
        [property: JsonProperty("color_index")] int ColorIndex
    );

    public record LineEntity(
        [property: JsonProperty("handle")] string Handle,
        [property: JsonProperty("layer")] string Layer,
        [property: JsonProperty("start")] Point2D Start,
        [property: JsonProperty("end")] Point2D End,
        [property: JsonProperty("length")] double Length,
        [property: JsonProperty("color_index")] int ColorIndex,
        [property: JsonProperty("linetype")] string Linetype
    );

    public record PolylineEntity(
        [property: JsonProperty("handle")] string Handle,
        [property: JsonProperty("layer")] string Layer,
        [property: JsonProperty("closed")] bool Closed,
        [property: JsonProperty("vertices")] List<Point2D> Vertices,
        [property: JsonProperty("area")] double Area,
        [property: JsonProperty("color_index")] int ColorIndex,
        [property: JsonProperty("linetype")] string Linetype
    );

    public record LayerInfo(
        [property: JsonProperty("name")] string Name,
        [property: JsonProperty("color_index")] int ColorIndex,
        [property: JsonProperty("on")] bool On,
        [property: JsonProperty("frozen")] bool Frozen,
        [property: JsonProperty("locked")] bool Locked
    );

    public record BlockDefinitionInfo(
        [property: JsonProperty("name")] string Name,
        [property: JsonProperty("description")] string Description,
        [property: JsonProperty("is_dynamic")] bool IsDynamic
    );

    public record BoundingBox(
        [property: JsonProperty("min")] Point2D Min,
        [property: JsonProperty("max")] Point2D Max
    );

    public record DwgDrawing(
        [property: JsonProperty("name")] string Name,
        [property: JsonProperty("units")] string Units,
        [property: JsonProperty("coordinate_system")] string CoordinateSystem,
        [property: JsonProperty("extents")] BoundingBox Extents,
        [property: JsonProperty("layers")] List<LayerInfo> Layers,
        [property: JsonProperty("block_definitions")] List<BlockDefinitionInfo> BlockDefinitions
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
        public static DwgContext ExtractContext()
        {
            try
            {
                var doc = AcApplication.DocumentManager.MdiActiveDocument;
                if (doc == null)
                {
                    return BuildEmptyContext("unknown", "unitless", "WCS");
                }

                var db = doc.Database;
                var blocks = new List<BlockRef>();
                var texts = new List<TextEntity>();
                var lines = new List<LineEntity>();
                var polylines = new List<PolylineEntity>();
                var layers = new List<LayerInfo>();
                var blockDefs = new List<BlockDefinitionInfo>();

                using (var tr = db.TransactionManager.StartTransaction())
                {
                    // Extract layer table
                    var lt = (LayerTable)tr.GetObject(db.LayerTableId, OpenMode.ForRead);
                    foreach (ObjectId lid in lt)
                    {
                        var ltr = tr.GetObject(lid, OpenMode.ForRead) as LayerTableRecord;
                        if (ltr == null) continue;
                        layers.Add(new LayerInfo(
                            Name: ltr.Name,
                            ColorIndex: ltr.Color.ColorIndex,
                            On: !ltr.IsOff,
                            Frozen: ltr.IsFrozen,
                            Locked: ltr.IsLocked
                        ));
                    }

                    // Extract block definitions
                    var bt = (BlockTable)tr.GetObject(db.BlockTableId, OpenMode.ForRead);
                    foreach (ObjectId bid in bt)
                    {
                        var btr = tr.GetObject(bid, OpenMode.ForRead) as BlockTableRecord;
                        if (btr == null || btr.IsLayout || btr.IsAnonymous) continue;
                        blockDefs.Add(new BlockDefinitionInfo(
                            Name: btr.Name,
                            Description: btr.Comments ?? "",
                            IsDynamic: btr.IsDynamicBlock
                        ));
                    }

                    // Extract model space entities
                    var ms = (BlockTableRecord)tr.GetObject(bt[BlockTableRecord.ModelSpace], OpenMode.ForRead);
                    foreach (ObjectId id in ms)
                    {
                        if (!id.IsValid || id.IsErased) continue;

                        var ent = tr.GetObject(id, OpenMode.ForRead) as Entity;
                        if (ent == null) continue;

                        switch (ent)
                        {
                            case BlockReference blockRef:
                                blocks.Add(BuildBlockRef(blockRef, tr, bt));
                                break;
                            case DBText dbText:
                                texts.Add(BuildTextEntity(dbText));
                                break;
                            case MText mText:
                                texts.Add(BuildMTextEntity(mText));
                                break;
                            case Line line:
                                lines.Add(BuildLineEntity(line));
                                break;
                            case Polyline polyline:
                                polylines.Add(BuildPolylineEntity(polyline));
                                break;
                        }
                    }

                    tr.Commit();
                }

                return BuildDwgContext(doc.Name, db.Insunits, db, blocks, texts, lines, polylines, layers, blockDefs);
            }
            catch (System.Exception)
            {
                return BuildEmptyContext("unknown", "unitless", "WCS");
            }
        }

        private static DwgContext BuildEmptyContext(string name, string units, string coordinateSystem)
        {
            var emptyBox = new BoundingBox(new Point2D(0, 0), new Point2D(0, 0));
            return new DwgContext(
                SchemaVersion: "1.0.0",
                RequestId: Guid.NewGuid().ToString(),
                Drawing: new DwgDrawing(
                    Name: name,
                    Units: units,
                    CoordinateSystem: coordinateSystem,
                    Extents: emptyBox,
                    Layers: new List<LayerInfo>(),
                    BlockDefinitions: new List<BlockDefinitionInfo>()),
                Blocks: new List<BlockRef>(),
                Texts: new List<TextEntity>(),
                Lines: new List<LineEntity>(),
                Polylines: new List<PolylineEntity>()
            );
        }

        private static DwgContext BuildDwgContext(
            string name,
            UnitsValue unitsValue,
            Database db,
            List<BlockRef> blocks,
            List<TextEntity> texts,
            List<LineEntity> lines,
            List<PolylineEntity> polylines,
            List<LayerInfo> layers,
            List<BlockDefinitionInfo> blockDefs)
        {
            var extents = new BoundingBox(
                new Point2D(db.Extmin.X, db.Extmin.Y),
                new Point2D(db.Extmax.X, db.Extmax.Y)
            );
            return new DwgContext(
                SchemaVersion: "1.1.0",
                RequestId: Guid.NewGuid().ToString(),
                Drawing: new DwgDrawing(
                    Name: name,
                    Units: MapUnits(unitsValue),
                    CoordinateSystem: "WCS",
                    Extents: extents,
                    Layers: layers,
                    BlockDefinitions: blockDefs),
                Blocks: blocks,
                Texts: texts,
                Lines: lines,
                Polylines: polylines
            );
        }

        private static string MapUnits(UnitsValue unitsValue)
        {
            return unitsValue switch
            {
                UnitsValue.Inches => "inch",
                UnitsValue.Feet => "foot",
                UnitsValue.Millimeters => "mm",
                UnitsValue.Centimeters => "cm",
                UnitsValue.Meters => "m",
                _ => "unitless",
            };
        }

        private static BlockRef BuildBlockRef(BlockReference blockRef, Transaction tr, BlockTable bt)
        {
            var attributes = new List<BlockAttribute>();
            if (blockRef.AttributeCollection != null)
            {
                foreach (ObjectId attId in blockRef.AttributeCollection)
                {
                    var att = tr.GetObject(attId, OpenMode.ForRead) as AttributeReference;
                    if (att == null) continue;
                    attributes.Add(new BlockAttribute(Tag: att.Tag, Value: att.TextString));
                }
            }

            // Read block definition for description and dynamic flag
            var description = "";
            var isDynamic = false;
            try
            {
                if (bt.Has(blockRef.Name))
                {
                    var btr = tr.GetObject(bt[blockRef.Name], OpenMode.ForRead) as BlockTableRecord;
                    if (btr != null)
                    {
                        description = btr.Comments ?? "";
                        isDynamic = btr.IsDynamicBlock;
                    }
                }
            }
            catch { }

            var scale = blockRef.ScaleFactors.X;

            return new BlockRef(
                Handle: blockRef.Handle.ToString(),
                Name: blockRef.Name,
                Layer: blockRef.Layer,
                Position: ToPoint2D(blockRef.Position),
                RotationDeg: blockRef.Rotation * (180.0 / Math.PI),
                Scale: scale,
                ColorIndex: blockRef.ColorIndex,
                IsDynamic: isDynamic,
                Description: description,
                Attributes: attributes
            );
        }

        private static string StripRtf(string raw)
        {
            if (string.IsNullOrEmpty(raw)) return "";
            // Remove MText format codes: {\fFont|...; ...} groups and \P paragraph breaks
            var s = Regex.Replace(raw, @"\{\\[^}]*\}", "");
            s = Regex.Replace(s, @"\\[A-Za-z]+[0-9.]*;?", " ");
            s = Regex.Replace(s, @"\{|\}", "");
            s = Regex.Replace(s, @"\s+", " ").Trim();
            return s;
        }

        private static TextEntity BuildTextEntity(DBText text)
        {
            var raw = text.TextString;
            return new TextEntity(
                Handle: text.Handle.ToString(),
                Value: raw,
                ValuePlain: StripRtf(raw),
                Layer: text.Layer,
                Position: ToPoint2D(text.Position),
                Height: text.Height,
                Style: text.TextStyleName ?? "",
                ColorIndex: text.ColorIndex
            );
        }

        private static TextEntity BuildMTextEntity(MText text)
        {
            var raw = text.Contents;
            return new TextEntity(
                Handle: text.Handle.ToString(),
                Value: raw,
                ValuePlain: StripRtf(raw),
                Layer: text.Layer,
                Position: ToPoint2D(text.Location),
                Height: text.TextHeight,
                Style: text.TextStyleName ?? "",
                ColorIndex: text.ColorIndex
            );
        }

        private static LineEntity BuildLineEntity(Line line)
        {
            return new LineEntity(
                Handle: line.Handle.ToString(),
                Layer: line.Layer,
                Start: ToPoint2D(line.StartPoint),
                End: ToPoint2D(line.EndPoint),
                Length: line.Length,
                ColorIndex: line.ColorIndex,
                Linetype: line.Linetype ?? "ByLayer"
            );
        }

        private static PolylineEntity BuildPolylineEntity(Polyline polyline)
        {
            var vertices = new List<Point2D>();
            for (var i = 0; i < polyline.NumberOfVertices; i++)
            {
                vertices.Add(ToPoint2D(polyline.GetPoint2dAt(i)));
            }

            double area = 0;
            try { area = polyline.Area; } catch { }

            return new PolylineEntity(
                Handle: polyline.Handle.ToString(),
                Layer: polyline.Layer,
                Closed: polyline.Closed,
                Vertices: vertices,
                Area: area,
                ColorIndex: polyline.ColorIndex,
                Linetype: polyline.Linetype ?? "ByLayer"
            );
        }

        private static Point2D ToPoint2D(Point3d point)
        {
            return new Point2D(point.X, point.Y);
        }

        private static Point2D ToPoint2D(Point2d point)
        {
            return new Point2D(point.X, point.Y);
        }
    }
}
