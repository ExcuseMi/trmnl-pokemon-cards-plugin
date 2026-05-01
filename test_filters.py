import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from backend.app import PROVIDERS

async def test_pokemon_filters():
    print(f"\n--- Testing POKEMON with Filters ---")
    provider = PROVIDERS['pokemon']
    
    # Test 1: Grass type
    print("Fetching Grass Pokemon...")
    card = await provider.refresh_card(pokemon_type='Grass')
    if card and 'Grass' in card['types']:
        print(f"Success! Found Grass: {card['name']}")
    else:
        print(f"Failed or wrong type: {card}")

    # Test 2: Rare rarity
    print("\nFetching Rare Pokemon...")
    card = await provider.refresh_card(rarity='Rare')
    if card and card['rarity'] == 'Rare':
        print(f"Success! Found Rare: {card['name']}")
    else:
        print(f"Failed or wrong rarity: {card}")

if __name__ == "__main__":
    asyncio.run(test_pokemon_filters())
