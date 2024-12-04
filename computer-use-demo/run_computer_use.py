import asyncio

from computer_use_demo.streamlit import main

DEFAULT_MESSAGE = """
Search Google Maps for restaurants within a 0.5-mile radius of the Barclays Center in Brooklyn. Filter results to include:

Cuisine type: (e.g., American, Italian, Asian fusion)
Price range: (e.g., $ to $$ or moderate)
Open for dinner at current time
Sorted by highest rating
Include restaurants with at least 4-star reviews

Provide the top 3 restaurant options with:

Restaurant name
Exact address
Current rating
Price range
Cuisine type
Brief description from reviews

Verify the current hours of operation for each restaurant to confirm they are open for dinner.
"""

asyncio.run(main(DEFAULT_MESSAGE))
