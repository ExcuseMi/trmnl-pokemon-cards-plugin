function transform(input) {
    var LABELS = {
        en:      { artist: 'Artist',       hp: 'HP', type: 'Type',       stage: 'Stage',      rarity: 'Rarity',      retreat: 'Retreat',  mark: 'Mark',          print: 'Print',    cards: 'Cards',  avg: 'CM Avg',    avg7: 'CM 7d',    set: 'Set',      tcg_market: 'TCG Mkt', tcg_low: 'TCG Low', released: 'Released' },
        fr:      { artist: 'Illustrateur', hp: 'PV', type: 'Type',       stage: 'Stade',      rarity: 'Rareté',      retreat: 'Retraite', mark: 'Marque',        print: 'Éd.',      cards: 'Cartes', avg: 'CM Moy',    avg7: 'CM 7j',    set: 'Série',    tcg_market: 'TCG Mkt', tcg_low: 'TCG Low', released: 'Date de sortie' },
        es:      { artist: 'Artista',      hp: 'PS', type: 'Tipo',       stage: 'Fase',       rarity: 'Rareza',      retreat: 'Retirada', mark: 'Marca',         print: 'Impr.',    cards: 'Cartas', avg: 'CM Prom',   avg7: 'CM 7d',    set: 'Serie',    tcg_market: 'TCG Mkt', tcg_low: 'TCG Low', released: 'Lanzamiento' },
        it:      { artist: 'Artista',      hp: 'PS', type: 'Tipo',       stage: 'Stadio',     rarity: 'Rarità',      retreat: 'Ritirata', mark: 'Marchio',       print: 'Stampa',   cards: 'Carte',  avg: 'CM Media',  avg7: 'CM 7g',    set: 'Serie',    tcg_market: 'TCG Mkt', tcg_low: 'TCG Low', released: 'Uscita' },
        'pt-br': { artist: 'Artista',      hp: 'PS', type: 'Tipo',       stage: 'Estágio',    rarity: 'Raridade',    retreat: 'Recuo',    mark: 'Marca',         print: 'Impr.',    cards: 'Cartas', avg: 'CM Méd',    avg7: 'CM 7d',    set: 'Coleção',  tcg_market: 'TCG Mkt', tcg_low: 'TCG Low', released: 'Lançamento' },
        de:      { artist: 'Illustrator',  hp: 'KP', type: 'Typ',        stage: 'Stufe',      rarity: 'Seltenheit',  retreat: 'Rückzug',  mark: 'Marke',         print: 'Druck',    cards: 'Karten', avg: 'CM Ø',      avg7: 'CM Ø 7T',  set: 'Set',      tcg_market: 'TCG Mkt', tcg_low: 'TCG Low', released: 'Erschienen' },
        ja:      { artist: 'イラスト',     hp: 'HP', type: 'タイプ',     stage: '進化段階',   rarity: 'レアリティ',  retreat: 'にげる',   mark: 'マーク',        print: '版',       cards: '収録数', avg: 'CM 平均',   avg7: 'CM 7日',   set: 'セット',   tcg_market: 'TCG 相場', tcg_low: 'TCG 安値', released: '発売日' },
        'zh-tw': { artist: '插畫師',       hp: 'HP', type: '屬性',       stage: '進化階段',   rarity: '稀有度',      retreat: '撤退',     mark: '標記',          print: '版本',     cards: '卡片數', avg: 'CM均價',    avg7: 'CM 7日',   set: '系列',     tcg_market: 'TCG行情', tcg_low: 'TCG低價', released: '發行日期' },
        id:      { artist: 'Artis',        hp: 'HP', type: 'Tipe',       stage: 'Tahap',      rarity: 'Kelangkaan',  retreat: 'Mundur',   mark: 'Tanda',         print: 'Cetakan',  cards: 'Kartu',  avg: 'CM Rata',   avg7: 'CM 7h',    set: 'Set',      tcg_market: 'TCG Mkt', tcg_low: 'TCG Low', released: 'Rilis' },
        th:      { artist: 'ศิลปิน',       hp: 'HP', type: 'ประเภท',    stage: 'วิวัฒน์',   rarity: 'หายาก',      retreat: 'ถอย',      mark: 'เครื่องหมาย',  print: 'พิมพ์',   cards: 'การ์ด', avg: 'CM เฉลี่ย', avg7: 'CM 7วัน', set: 'ชุด',      tcg_market: 'TCG ราคา', tcg_low: 'TCG ต่ำ', released: 'วันวางจำหน่าย' },
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
