
import ee

ee.Initialize(project="maj-project-513220")

districts = (
    ee.FeatureCollection("FAO/GAUL/2025/level2")
    .filter(ee.Filter.eq("GAUL0_NAME", "India"))
    .filter(ee.Filter.eq("GAUL1_NAME", "Meghalaya"))
)

names = districts.aggregate_array("GAUL2_NAME").getInfo()

print("\nMeghalaya districts in GAUL 2025:")
for name in sorted(names):
    print(" -", name)

targets = ["East Jaintia Hills", "West Jaintia Hills"]

found = [
    name for name in names
    if name.lower().strip() in [t.lower() for t in targets]
]

print("\nMatched districts:", found)

if len(set(found)) == 2:
    selected = districts.filter(
        ee.Filter.inList("GAUL2_NAME", targets)
    )
    area = selected.geometry().area(maxError=100).divide(1e6)
    print("Combined area (sq km):", area.getInfo())
    print("Both districts found. Inspect geometry before use.")
else:
    print("Boundary not verified. Do not run processing yet.")
