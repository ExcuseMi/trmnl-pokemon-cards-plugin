function transform(input) {
  var raw = Array.isArray(input.data) ? input.data : [];

  var items = raw.slice(0, 4);

  return { items: items };
}
