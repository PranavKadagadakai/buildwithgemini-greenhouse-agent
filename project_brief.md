# My agent: greenhouse-agent
One-liner: A conversational agent that helps plant parents care for houseplants and adopt new plants with a catalog of greenhouse plants and care guides.

Tool coverage:
- Memory: User's plant care experience level, home sunlight conditions, pet ownership (for pet safety), and watering logs
- Tools: Look up plant catalog & care requirements in Firestore, update care history, query greenhouse stock
- Catalog/UI: Collection of greenhouse plants (name, species, light, water, difficulty, price, in_stock) rendered as rich cards
- Image gen: Generate visuals of plants in home settings and seasonal blooms via gemini-3.1-flash-lite-image
- Sandbox: Calculate watering intervals and fertilizer dilutions based on pot size and room conditions

Recommended for every project: memory, storage, tools, image generation, A2UI
Agent-specific / stretch (pick what fits): Perenual Botanical API for live species data, code sandbox for watering calculations, Cloud Trace
