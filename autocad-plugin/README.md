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
