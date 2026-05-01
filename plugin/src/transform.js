function transform(input) {
  var d = (input.data) || {};
  var types = Array.isArray(d.types) ? d.types : [];
  
  // Determine stat label based on ID or content if game info not directly available
  // But we can check the polling_url in trmnl context if needed, 
  // though it's easier to just detect it from the data content or assume Pokemon if it's just a number.
  var statLabel = 'HP';
  var hp = d.hp || '';
  if (hp.indexOf('/') !== -1) {
    if (hp.indexOf('Lvl') === -1) {
      // Likely MTG (P/T) or YGO (ATK/DEF)
      // We can try to guess or just use 'Stats'
      statLabel = 'Stats'; 
    }
  }

  return {
    card: {
      name: d.name || '',
      hp: hp,
      stat_label: statLabel,
      types_str: types.join(' · '),
      rarity: d.rarity || '',
      set_name: d.set_name || '',
      image_large: d.image_large || '',
      image_small: d.image_small || '',
    }
  };
}
