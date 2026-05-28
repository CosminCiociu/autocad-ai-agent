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

## Plugin scaffold (this repo)

Files added as a minimal scaffold that you should adapt to your AutoCAD environment:

- `AutocadPlugin.csproj` - sample SDK project file (adjust `TargetFramework` to match AutoCAD runtime, e.g. `net48`).
- `Commands.cs` - entry point method `AiExtract(outPath)` demonstrating calling the extractor and serializer.
- `BlockReader.cs` - placeholder extraction types and `ExtractContext()` that currently returns a minimal JSON-compatible object. Replace with AutoCAD .NET API code.
- `EntitySerializer.cs` - helper that writes the context object to a JSON file using `Newtonsoft.Json`.

## How to implement real extraction

1. Change `AutocadPlugin.csproj` TargetFramework to the required .NET version for your AutoCAD version.
2. Reference AutoCAD .NET assemblies (e.g., `AcMgd.dll`, `AcDbMgd.dll`) and set `CopyLocal=false` as appropriate.
3. Implement `BlockReader.ExtractContext()` using `Transaction`, `BlockTableRecord`, `BlockReference`, `DBText` / `MText`, `Polyline` classes from the AutoCAD API.
4. Use `SchemaValidation.SchemaValidator` to validate generated JSON before writing/sending it to the AI server.

This scaffold is intentionally minimal to be portable and to avoid depending on AutoCAD at CI time.
