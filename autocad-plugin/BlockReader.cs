using System;
using System.Collections.Generic;
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
        [property: JsonProperty("attributes")] List<BlockAttribute>? Attributes
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

                using (var tr = db.TransactionManager.StartTransaction())
                {
                    var bt = (BlockTable)tr.GetObject(db.BlockTableId, OpenMode.ForRead);
                    var ms = (BlockTableRecord)tr.GetObject(bt[BlockTableRecord.ModelSpace], OpenMode.ForRead);

                    foreach (ObjectId id in ms)
                    {
                        if (!id.IsValid || id.IsErased) continue;

                        var ent = tr.GetObject(id, OpenMode.ForRead) as Entity;
                        if (ent == null) continue;

                        switch (ent)
                        {
                            case BlockReference blockRef:
                                blocks.Add(BuildBlockRef(blockRef, tr));
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

                return BuildDwgContext(doc.Name, db.Insunits, blocks, texts, lines, polylines);
            }
            catch (System.Exception)
            {
                return BuildEmptyContext("unknown", "unitless", "WCS");
            }
        }

        private static DwgContext BuildEmptyContext(string name, string units, string coordinateSystem)
        {
            return new DwgContext(
                SchemaVersion: "1.0.0",
                RequestId: Guid.NewGuid().ToString(),
                Drawing: new DwgDrawing(Name: name, Units: units, CoordinateSystem: coordinateSystem),
                Blocks: new List<BlockRef>(),
                Texts: new List<TextEntity>(),
                Lines: new List<LineEntity>(),
                Polylines: new List<PolylineEntity>()
            );
        }

        private static DwgContext BuildDwgContext(
            string name,
            UnitsValue unitsValue,
            List<BlockRef> blocks,
            List<TextEntity> texts,
            List<LineEntity> lines,
            List<PolylineEntity> polylines)
        {
            return new DwgContext(
                SchemaVersion: "1.0.0",
                RequestId: Guid.NewGuid().ToString(),
                Drawing: new DwgDrawing(Name: name, Units: MapUnits(unitsValue), CoordinateSystem: "WCS"),
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

        private static BlockRef BuildBlockRef(BlockReference blockRef, Transaction tr)
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

            return new BlockRef(
                Handle: blockRef.Handle.ToString(),
                Name: blockRef.Name,
                Layer: blockRef.Layer,
                Position: ToPoint2D(blockRef.Position),
                RotationDeg: blockRef.Rotation * (180.0 / Math.PI),
                Attributes: attributes.Count > 0 ? attributes : null
            );
        }

        private static TextEntity BuildTextEntity(DBText text)
        {
            return new TextEntity(
                Handle: text.Handle.ToString(),
                Value: text.TextString,
                Layer: text.Layer,
                Position: ToPoint2D(text.Position),
                Height: text.Height
            );
        }

        private static TextEntity BuildMTextEntity(MText text)
        {
            return new TextEntity(
                Handle: text.Handle.ToString(),
                Value: text.Contents,
                Layer: text.Layer,
                Position: ToPoint2D(text.Location),
                Height: text.TextHeight
            );
        }

        private static LineEntity BuildLineEntity(Line line)
        {
            return new LineEntity(
                Handle: line.Handle.ToString(),
                Layer: line.Layer,
                Start: ToPoint2D(line.StartPoint),
                End: ToPoint2D(line.EndPoint)
            );
        }

        private static PolylineEntity BuildPolylineEntity(Polyline polyline)
        {
            var vertices = new List<Point2D>();
            for (var i = 0; i < polyline.NumberOfVertices; i++)
            {
                vertices.Add(ToPoint2D(polyline.GetPoint2dAt(i)));
            }

            return new PolylineEntity(
                Handle: polyline.Handle.ToString(),
                Layer: polyline.Layer,
                Closed: polyline.Closed,
                Vertices: vertices
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
