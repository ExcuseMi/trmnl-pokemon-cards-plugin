function transform(input) {
    var LABELS = {
        en:      { artist: 'Artist',       hp: 'HP', type: 'Type',       stage: 'Stage',      rarity: 'Rarity',      retreat: 'Retreat',  mark: 'Mark',          print: 'Print',    cards: 'Cards',  number: 'No.',   avg: 'CM Avg',    avg7: 'CM 7d',    set: 'Set',      serie: 'Series',   tcg_market: 'TCG Mkt', tcg_low: 'TCG Low', released: 'Released', evolve_from: 'Evolve from', description: 'Description' },
        fr:      { artist: 'Illustrateur', hp: 'PV', type: 'Type',       stage: 'Stade',      rarity: 'Rareté',      retreat: 'Retraite', mark: 'Marque',        print: 'Éd.',      cards: 'Cartes', number: 'No.',   avg: 'CM Moy',    avg7: 'CM 7j',    set: 'Set',      serie: 'Série',    tcg_market: 'TCG Mkt', tcg_low: 'TCG Low', released: 'Date de sortie', evolve_from: 'Évolution de', description: 'Description' },
        es:      { artist: 'Artista',      hp: 'PS', type: 'Tipo',       stage: 'Fase',       rarity: 'Rareza',      retreat: 'Retirada', mark: 'Marca',         print: 'Impr.',    cards: 'Cartas', number: 'No.',   avg: 'CM Prom',   avg7: 'CM 7d',    set: 'Set',      serie: 'Serie',    tcg_market: 'TCG Mkt', tcg_low: 'TCG Low', released: 'Lanzamiento', evolve_from: 'Evoluciona de', description: 'Descripción' },
        it:      { artist: 'Artista',      hp: 'PS', type: 'Tipo',       stage: 'Stadio',     rarity: 'Rarità',      retreat: 'Ritirata', mark: 'Marchio',       print: 'Stampa',   cards: 'Carte',  number: 'No.',   avg: 'CM Media',  avg7: 'CM 7g',    set: 'Set',      serie: 'Serie',    tcg_market: 'TCG Mkt', tcg_low: 'TCG Low', released: 'Uscita', evolve_from: 'Evolve da', description: 'Descrizione' },
        'pt-br': { artist: 'Artista',      hp: 'PS', type: 'Tipo',       stage: 'Estágio',    rarity: 'Raridade',    retreat: 'Recuo',    mark: 'Marca',         print: 'Impr.',    cards: 'Cartas', number: 'No.',   avg: 'CM Méd',    avg7: 'CM 7d',    set: 'Set',      serie: 'Série',    tcg_market: 'TCG Mkt', tcg_low: 'TCG Low', released: 'Lançamento', evolve_from: 'Evolui de', description: 'Descrição' },
        de:      { artist: 'Illustrator',  hp: 'KP', type: 'Typ',        stage: 'Stufe',      rarity: 'Seltenheit',  retreat: 'Rückzug',  mark: 'Marke',         print: 'Druck',    cards: 'Karten', number: 'Nr.',   avg: 'CM Ø',      avg7: 'CM Ø 7T',  set: 'Set',      serie: 'Serie',    tcg_market: 'TCG Mkt', tcg_low: 'TCG Low', released: 'Erschienen', evolve_from: 'Entwickelt von', description: 'Beschreibung' },
        ja:      { artist: 'イラスト',     hp: 'HP', type: 'タイプ',     stage: '進化段階',   rarity: 'レアリティ',  retreat: 'にげる',   mark: 'マーク',        print: '版',       cards: '収録数', number: '番号',  avg: 'CM 平均',   avg7: 'CM 7日',   set: 'セット',   serie: 'シリーズ', tcg_market: 'TCG 相場', tcg_low: 'TCG 安値', released: '発売日', evolve_from: '進化元', description: '説明' },
        'zh-tw': { artist: '插畫師',       hp: 'HP', type: '屬性',       stage: '進化階段',   rarity: '稀有度',      retreat: '撤退',     mark: '標記',          print: '版本',     cards: '卡片數', number: '編號',  avg: 'CM均價',    avg7: 'CM 7日',   set: '系列',     serie: '系列名',   tcg_market: 'TCG行情', tcg_low: 'TCG低價', released: '發行日期', evolve_from: '進化自', description: '描述' },
        id:      { artist: 'Artis',        hp: 'HP', type: 'Tipe',       stage: 'Tahap',      rarity: 'Kelangkaan',  retreat: 'Mundur',   mark: 'Tanda',         print: 'Cetakan',  cards: 'Kartu',  number: 'No.',   avg: 'CM Rata',   avg7: 'CM 7h',    set: 'Set',      serie: 'Seri',     tcg_market: 'TCG Mkt', tcg_low: 'TCG Low', released: 'Rilis', evolve_from: 'Evolusi dari', description: 'Deskripsi' },
        th:      { artist: 'ศิลปิน',       hp: 'HP', type: 'ประเภท',    stage: 'วิวัฒน์',   rarity: 'หายาก',      retreat: 'ถอย',      mark: 'เครื่องหมาย',  print: 'พิมพ์',   cards: 'การ์ด', number: 'เลขที่', avg: 'CM เฉลี่ย', avg7: 'CM 7วัน', set: 'ชุด',      serie: 'ซีรีส์',  tcg_market: 'TCG ราคา', tcg_low: 'TCG ต่ำ', released: 'วันวางจำหน่าย', evolve_from: 'วิวัฒนาการจาก', description: 'คำอธิบาย' },
      };

  var raw = Array.isArray(input.data) ? input.data : [];
  var lang = ((((input.trmnl || {}).plugin_settings || {}).custom_fields_values || {}).language || 'en').toLowerCase();
  var labels = LABELS[lang] || LABELS['en'];

  return {
    items: raw.slice(0, 4),
    labels: labels,
    pool_warning: typeof input.pool_warning === 'number' ? input.pool_warning : null,
  };
}