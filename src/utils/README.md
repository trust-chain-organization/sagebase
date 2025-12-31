# ⚠️ DEPRECATED: Utils Directory

This directory contains **backward compatibility stubs only**. Utilities have been moved to the infrastructure layer as part of the Clean Architecture migration.

## Migration Status

**Current Phase**: Phase 3/5 Complete
**Removal Timeline**: Phase 5 (Final Cleanup)

## Deprecated Modules

The following modules are **deprecated** and will be removed in Phase 5:

| Deprecated Import | New Location | Status |
|-------------------|--------------|--------|
| `src.utils.text_extractor` | `src.infrastructure.utilities.text_extractor` | ⚠️ Deprecated |
| `src.utils.japan_map` | `src.infrastructure.utilities.japan_map` | ⚠️ Deprecated |
| `src.utils.gcs_storage` | `src.infrastructure.storage.gcs_client` | ✅ Migrated (Issue #792) |

## How to Update Your Code

### Standard Imports

**Before (Deprecated)**:
```python
from src.utils.text_extractor import extract_text_from_pdf
from src.utils.japan_map import create_japan_map
```

**After (Recommended)**:
```python
from src.infrastructure.utilities.text_extractor import extract_text_from_pdf
from src.infrastructure.utilities.japan_map import create_japan_map
```

### Alternative (Using Module Import)

**Before**:
```python
from src.utils import text_extractor
```

**After**:
```python
from src.infrastructure import utilities
# or
from src.infrastructure.utilities import text_extractor
```

## Deprecation Warnings

When importing from the old location, you will see warnings like:

```
DeprecationWarning: Importing from 'src.utils.text_extractor' is deprecated.
Use 'src.infrastructure.utilities.text_extractor' instead.
```

## GCS Storage Note

`src.utils.gcs_storage` has been **migrated** to `src.infrastructure.storage.gcs_client` (Issue #792). This provides the low-level GCS client, while `src.infrastructure.external.gcs_storage_service` implements the `IStorageService` interface.

## Contributing

When adding new utilities:
- ❌ **Do NOT** add new files to `src/utils/`
- ✅ **Do** use `src/infrastructure/utilities/` for new utilities
- ✅ **Do** update existing imports when you touch a file

---

**Last Updated**: 2025-11-01 (Phase 3 completion)
