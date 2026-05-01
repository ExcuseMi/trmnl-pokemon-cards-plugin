function transform(input) {
  var raw = Array.isArray(input.data) ? input.data : [];

  var items = raw.slice(0, 4).map(function(d) {
    var types = Array.isArray(d.types) ? d.types : [];
    return {
      name:        d.name || '',
      hp:          d.hp ? String(d.hp) : '',
      types_str:   types.join(' · '),
      rarity:      d.rarity || '',
      set_name:    d.set_name || '',
      set_logo:    d.set_logo || '',
      image_large: d.image_large || '',
      image_small: d.image_small || '',
    };
  });

  return { items: items };
}
