"""Quick test — run the pipeline with sample FTG data.
Usage: python test_pipeline.py

Can also run with real sanitized data files:
  python test_pipeline.py --use-files
"""
import sys
from pipeline import run_pipeline


def load_from_files():
    """Load PRD and code from sanitized test data files."""
    with open("test_data/ftg_prd.txt", "r") as f:
        prd = f.read()
    with open("test_data/ftg_code.txt", "r") as f:
        code = f.read()
    return prd, code


# Sample PRD text (simplified FTG flow)
SAMPLE_PRD = """
FTG (First Time Good) Dimension Capture Flow - Revamped

The new FTG flow has 4 screens:

Screen 1 - SKU Search:
- User scans barcode or types SKU in search box
- Autocomplete results appear as product cards
- User taps a product card to select it

Screen 2 - Packaging Options:
- Three card options: SIOB (Ships In Own Box), SIOCB (Ships In Own Case Box), Repackaged
- If SIOCB selected, an "Items Per Box" input appears (min 2, max 10000)
- Next button is disabled until an option is selected

Screen 3 - Product Identifiers:
- Product Category dropdown (mandatory)
- Scannable ID input (optional)
- Product Image URL input (optional, must be http/https)
- Next button to proceed

Screen 4 - Dimension & Weight Capture:
- Tab selector: V-Measure (default) | Manual
- V-Measure mode: shows barcode, user places product on machine and scans
  - Auto-polls API every 2 seconds for dimensions
  - Shows L x W x H and Weight when received
  - Recapture button available
  - Error if dimensions exceed machine limits
- Manual mode: requires UMS permission
  - L, B, H inputs (max 999 cm, 2 decimal places)
  - Weight input (max 2000 kg, 3 decimal places)
  - Warning if values are within V-Measure range
- Save Dimensions button to complete
"""

SAMPLE_CODE = """
// Simplified FTG code (Kotlin-like pseudocode, sanitized)

enum class ScreenState { PACKAGING_OPTIONS, PRODUCT_IDENTIFIERS, DIMENSION_WEIGHT }
enum class PackagingOption { SIOB, SIOCB, REPACKAGED }
enum class DimensionMode { VMEASURE, MANUAL }

// SKU Search Screen
fun onSearchTextChanged(query: String) {
    if (query.length >= 3) fetchAutocompleteResults(query)
}
fun onProductSelected(product: Product) {
    navigateTo(ScreenState.PACKAGING_OPTIONS)
}

// Packaging Options Screen
fun onPackagingOptionSelected(option: PackagingOption) {
    selectedPackaging = option
    if (option == PackagingOption.SIOCB) showItemsPerBoxInput()
    btnNext.isEnabled = true
}
fun validatePackagingOptions(): Boolean {
    if (selectedPackaging == SIOCB && (itemsPerBox < 2 || itemsPerBox > 10000)) return false
    return selectedPackaging != null
}

// Product Identifiers Screen
fun validateIdentifiers(): Boolean {
    if (isSdpEnabled && productCategory.isEmpty()) return false
    if (imageUrl.isNotEmpty() && !imageUrl.startsWith("http")) return false
    return true
}

// Dimension & Weight Screen
fun onVmeasureTabSelected() { dimensionMode = VMEASURE; startPolling() }
fun onManualTabSelected() {
    if (!hasUmsPermission()) { showError("No permission for Manual mode"); return }
    dimensionMode = MANUAL
}
fun startVmDimensionPolling() { /* polls every 2 seconds */ }
fun validateDimensions(): Boolean {
    if (dimensionMode == MANUAL && isWithinVmeasureRange()) {
        showWarning("Values within V-Measure range. Use V-Measure instead.")
        return false
    }
    return length > 0 && width > 0 && height > 0 && weight > 0
}
fun onSaveDimensions() {
    if (validateDimensions()) { saveToDB(); showSuccess(); navigateBack() }
}
"""

if __name__ == "__main__":
    print("=" * 60)
    print("🧠 Train the Brain — Pipeline Test")
    print("=" * 60)

    if "--use-files" in sys.argv:
        print("📂 Loading from test_data/ files...")
        prd, code = load_from_files()
    else:
        print("📝 Using inline sample data...")
        prd, code = SAMPLE_PRD, SAMPLE_CODE

    result = run_pipeline(
        prd_text=prd,
        code_text=code,
        workflow_name="FTG Dimension Capture (Revamped)",
        generate_video=False,  # set True once you have screenshots
    )

    print("\n" + "=" * 60)
    print("📋 MANIFEST:")
    print(result.manifest.model_dump_json(indent=2))

    print("\n" + "=" * 60)
    print("📝 QUIZ:")
    print(result.assessment.model_dump_json(indent=2))

    if result.video_path:
        print(f"\n🎬 VIDEO: {result.video_path}")
