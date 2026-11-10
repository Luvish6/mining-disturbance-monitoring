
import ee

DISTRICT_NAMES = [
    "East Jaintia Hills",
    "West Jaintia Hills",
]

def get_study_area():
    districts = (
        ee.FeatureCollection("FAO/GAUL/2025/level2")
        .filter(ee.Filter.eq("GAUL0_NAME", "India"))
        .filter(ee.Filter.eq("GAUL1_NAME", "Meghalaya"))
        .filter(ee.Filter.inList("GAUL2_NAME", DISTRICT_NAMES))
    )
    return districts

def verify_boundary(fc):
    count = fc.size().getInfo()

    if count != 2:
        raise RuntimeError(
            f"Expected 2 districts, found {count}."
        )

    names = fc.aggregate_array("GAUL2_NAME").getInfo()

    if set(names) != set(DISTRICT_NAMES):
        raise RuntimeError(
            f"Unexpected district names: {names}"
        )

    area_km2 = (
        fc.geometry()
        .area(maxError=100)
        .divide(1e6)
        .getInfo()
    )

    print("Study area:", names)
    print(f"Combined area: {area_km2:.2f} km²")

    return fc.geometry()
