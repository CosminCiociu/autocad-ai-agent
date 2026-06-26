# AutoCAD Plugin Notes

This folder contains plugin-side code for DWG extraction, action execution, and schema validation.

## Current state

- Added JSON schema validation helper in `SchemaValidation/`.
- Validation uses `Newtonsoft.Json` and `Newtonsoft.Json.Schema`.

## Integration steps

1. Add package references in your plugin project:
   - `Newtonsoft.Json`
   - `Newtonsoft.Json.Schema`
2. Initialize validator with schema path (example):
   - `..\\shared\\schemas`
3. Validate incoming/outgoing JSON payloads before execution.

## Example usage

```csharp
var validator = new SchemaValidator(@"..\\shared\\schemas");
var contextResult = validator.ValidateDwgContext(contextJson);
if (!contextResult.IsValid)
{
    // return SCHEMA_INVALID error to caller
}
```

## Plugin command stubs

The scaffold now includes the following command entry points:

- `AiPing()` - plugin health check.
- `AiExtract(string outPath)` - extract DWG context and serialize it to JSON.
- `AiAnalyze(string serverBaseUrl, string userCommand, string outputPath = null, string? schemaDirectory = null)` - send extracted context to the AI server and store the action plan.
- `AiExecute(string planPath, string? schemaDirectory = null, bool previewOnly = false, string? reportPath = null)` - deserialize an action plan, optionally validate it, preview or execute it, and store an execution report.

Example usage:

```csharp
Commands.AiPing();
Commands.AiExtract(@"C:\temp\dwg_context.json", @"..\shared\schemas");
Commands.AiAnalyze("http://127.0.0.1:8000", "insert block on layer A", @"C:\temp\action_plan.json", @"..\shared\schemas");
Commands.AiExecute(@"C:\temp\action_plan.json", @"..\shared\schemas", previewOnly: true, reportPath: @"C:\temp\execution_report.json");
```

## Plugin scaffold (this repo)

Files added as a minimal scaffold that you should adapt to your AutoCAD environment:

- `AutocadPlugin.csproj` - sample SDK project file (adjust `TargetFramework` to match AutoCAD runtime, e.g. `net48`).
- `Commands.cs` - entry point methods `AiPing()` and `AiExtract(outPath)` demonstrating calling the extractor and serializer.
- `BlockReader.cs` - extraction types and `ExtractContext()` that currently returns a minimal JSON-compatible object. Replace with AutoCAD .NET API code.
- `EntitySerializer.cs` - helper that writes the context object to a JSON file using `Newtonsoft.Json`.

## How to implement real extraction

1. For AutoCAD 2024, target `net48`.
2. Reference AutoCAD .NET assemblies from the AutoCAD 2024 install folder:
   - `AcCoreMgd.dll`
   - `AcDbMgd.dll`
   - `AcMgd.dll`
3. Implement `BlockReader.ExtractContext()` using `Transaction`, `BlockTableRecord`, `BlockReference`, `DBText` / `MText`, `Polyline` classes from the AutoCAD API.
4. Implement `AiPing()` as a simple plugin health check before using extraction.
5. Use `SchemaValidation.SchemaValidator` to validate generated JSON before writing/sending it to the AI server.
6. The first end-to-end action we can complete safely is `find_entities`, because it can resolve matches from the extracted context without mutating the drawing.

This scaffold is intentionally minimal to be portable and to avoid depending on AutoCAD at CI time.
