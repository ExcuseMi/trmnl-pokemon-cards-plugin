function transform(input) {
  var rawCards = Array.isArray(input.data) ? input.data : (input.data ? [input.data] : []);
  
  var cards = rawCards.map(function(d) {
    var types = Array.isArray(d.types) ? d.types : [];
    var statLabel = 'HP';
    var hp = d.hp || '';
    if (hp.indexOf('/') !== -1) {
      if (hp.indexOf('Lvl') === -1) {
        statLabel = 'Stats'; 
      }
    }
    
    return {
      name: d.name || '',
      hp: hp,
      stat_label: statLabel,
      types_str: types.join(' · '),
      rarity: d.rarity || '',
      set_name: d.set_name || '',
      set_image: d.set_image || '',
      image_large: d.image_large || '',
      image_small: d.image_small || '',
    };
  });

  return {
    card: cards.length > 0 ? cards[0] : {
      name: '',
      hp: '',
      stat_label: 'HP',
      types_str: '',
      rarity: '',
      set_name: '',
      set_image: '',
      image_large: '',
      image_small: '',
    },
    cards: cards
  };
}
