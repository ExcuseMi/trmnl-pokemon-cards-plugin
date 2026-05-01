function transform(input) {
  var LABELS = {
    en:      { artist: 'Artist',       hp: 'HP', type: 'Type',       stage: 'Stage',      rarity: 'Rarity',      retreat: 'Retreat',  mark: 'Mark',          print: 'Print',    cards: 'Cards',  avg: 'Avg',    avg7: '7d avg',    set: 'Set'      },
    fr:      { artist: 'Illustrateur', hp: 'PV', type: 'Type',       stage: 'Stade',      rarity: 'Rareté',      retreat: 'Retraite', mark: 'Marque',        print: 'Éd.',      cards: 'Cartes', avg: 'Moy',    avg7: 'Moy 7j',    set: 'Série'    },
    es:      { artist: 'Artista',      hp: 'PS', type: 'Tipo',       stage: 'Fase',       rarity: 'Rareza',      retreat: 'Retirada', mark: 'Marca',         print: 'Impr.',    cards: 'Cartas', avg: 'Prom',   avg7: 'Prom 7d',   set: 'Serie'    },
    it:      { artist: 'Artista',      hp: 'PS', type: 'Tipo',       stage: 'Stadio',     rarity: 'Rarità',      retreat: 'Ritirata', mark: 'Marchio',       print: 'Stampa',   cards: 'Carte',  avg: 'Media',  avg7: 'Media 7g',  set: 'Serie'    },
    'pt-br': { artist: 'Artista',      hp: 'PS', type: 'Tipo',       stage: 'Estágio',    rarity: 'Raridade',    retreat: 'Recuo',    mark: 'Marca',         print: 'Impr.',    cards: 'Cartas', avg: 'Méd',    avg7: 'Méd 7d',    set: 'Coleção'  },
    de:      { artist: 'Illustrator',  hp: 'KP', type: 'Typ',        stage: 'Stufe',      rarity: 'Seltenheit',  retreat: 'Rückzug',  mark: 'Marke',         print: 'Druck',    cards: 'Karten', avg: 'Ø',      avg7: 'Ø 7T',      set: 'Set'      },
    ja:      { artist: 'イラスト',     hp: 'HP', type: 'タイプ',     stage: '進化段階',   rarity: 'レアリティ',  retreat: 'にげる',   mark: 'マーク',        print: '版',       cards: '収録数', avg: '平均',   avg7: '7日平均',   set: 'セット'   },
    'zh-tw': { artist: '插畫師',       hp: 'HP', type: '屬性',       stage: '進化階段',   rarity: '稀有度',      retreat: '撤退',     mark: '標記',          print: '版本',     cards: '卡片數', avg: '均價',   avg7: '7日均價',   set: '系列'     },
    id:      { artist: 'Artis',        hp: 'HP', type: 'Tipe',       stage: 'Tahap',      rarity: 'Kelangkaan',  retreat: 'Mundur',   mark: 'Tanda',         print: 'Cetakan',  cards: 'Kartu',  avg: 'Rata',   avg7: 'Rata 7h',   set: 'Set'      },
    th:      { artist: 'ศิลปิน',       hp: 'HP', type: 'ประเภท',    stage: 'วิวัฒน์',   rarity: 'หายาก',      retreat: 'ถอย',      mark: 'เครื่องหมาย',  print: 'พิมพ์',   cards: 'การ์ด', avg: 'เฉลี่ย', avg7: 'เฉลี่ย 7วัน', set: 'ชุด'  },
  };

  var raw = Array.isArray(input.data) ? input.data : [];
  var lang = ((((input.trmnl || {}).plugin_settings || {}).custom_fields_values || {}).language || 'en').toLowerCase();
  var labels = LABELS[lang] || LABELS['en'];

  return {
    items: raw.slice(0, 4),
    labels: labels,
  };
}
