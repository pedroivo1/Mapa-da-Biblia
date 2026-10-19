// Constantes da linha do tempo: eixo do tempo (SEGMENTOS), nomes de reinos e grupos, modos de
// filtro de livros, marcos e colunas. Sem estado.
// Parte da linha do tempo (linha-do-tempo/index.html); ligada às outras pelo objeto global LT.
(function () {
  "use strict";

  var LT = (window.LT = window.LT || {});

  // Anos: a.C. positivo, d.C. negativo. Cada trecho tem a sua escala (px por ano).
  var AXIS_INICIO = 2400;
  var AXIS_FIM = -100;
  var SEGMENTOS = [
    { de: 2400, ate: 2200, px: 0.8 },
    { de: 2200, ate: 1450, px: 1.5 },
    { de: 1450, ate: 1051, px: 2 },
    { de: 1051, ate: 420, px: 5 },
    { de: 420, ate: 63, px: 1.5 },
    { de: 63, ate: -100, px: 5 }
  ];
  var ESCALA = 1.4; // aumenta ou reduz a altura do mapa inteiro
  var TOP = 12;
  var ALTURA = TOP * 2;
  SEGMENTOS.forEach(function (s) {
    s.px *= ESCALA;
    s.off = ALTURA - TOP * 2;
    ALTURA += (s.de - s.ate) * s.px;
  });

  var REINO = { unido: "Reino unido", juda: "Judá", israel: "Israel", ambos: "Judá e Israel", nenhum: "—" };
  var AVALIACAO = { bom: "Fez o que era reto", mau: "Fez o que era mau", misto: "Misto" };
  var GRUPO = {
    lei: "Lei",
    historia: "Histórico",
    poesia: "Poético e sapiencial",
    evangelho: "Evangelho",
    atos: "Histórico (NT)",
    carta: "Carta",
    apocalipse: "Apocalíptico",
    "profeta-maior": "Profeta maior",
    "profeta-menor": "Profeta menor"
  };
  // grupos de livros do filtro (Livros)
  var AT = "Antigo Testamento", NT = "Novo Testamento";
  var MODOS = {
    almeida: {
      nome: "Almeida",
      grupos: [
        { id: "lei", nome: "Pentateuco", ta: AT },
        { id: "historia", nome: "Históricos", ta: AT },
        { id: "poesia", nome: "Poéticos e sapienciais", ta: AT },
        { id: "profeta-maior", nome: "Profetas maiores", ta: AT },
        { id: "profeta-menor", nome: "Profetas menores", ta: AT },
        { id: "evangelho", nome: "Evangelhos", ta: NT },
        { id: "atos", nome: "Histórico", ta: NT },
        { id: "carta", nome: "Cartas", ta: NT },
        { id: "apocalipse", nome: "Profético", ta: NT }
      ]
    },
    simples: {
      nome: "Simplificada",
      grupos: [
        { id: "lei", nome: "Lei", ta: AT },
        { id: "historia", nome: "Históricos", ta: AT },
        { id: "poesia", nome: "Poéticos", ta: AT },
        { id: "profeta", nome: "Profetas", ta: AT },
        { id: "historico-nt", nome: "Históricos", ta: NT },
        { id: "carta", nome: "Cartas", ta: NT },
        { id: "apocalipse", nome: "Proféticos", ta: NT }
      ]
    }
  };
  var JUNTA = { "profeta-maior": "profeta", "profeta-menor": "profeta", evangelho: "historico-nt", atos: "historico-nt" };
  var MARCOS = [
    { ano: 2166, nome: "Abraão", texto: "Chamado de Abraão (data aproximada). Começa a linhagem dos patriarcas.", ref: "Gn 12:1-4" },
    { ano: 1876, nome: "Egito", texto: "Jacó e a família descem ao Egito, onde José governa.", ref: "Gn 46" },
    { ano: 1446, nome: "Êxodo", texto: "Israel sai do Egito sob Moisés e chega ao Sinai. A data do êxodo é debatida (c. 1446 ou c. 1270 a.C.).", ref: "Êx 12–19" },
    { ano: 1406, nome: "Canaã", texto: "Israel atravessa o Jordão sob Josué e entra em Canaã.", ref: "Js 3–4" },
    { ano: 1051, nome: "Monarquia", texto: "Saul torna-se o primeiro rei de Israel.", ref: "1Sm 9–11" },
    { ano: 931, nome: "Divisão", texto: "O reino se divide: Judá com Roboão e Israel com Jeroboão I.", ref: "1Rs 12" },
    { ano: 722, nome: "Samaria", texto: "A Assíria conquista Samaria e termina o reino do norte.", ref: "2Rs 17" },
    { ano: 586, nome: "Jerusalém", texto: "A Babilônia destrói Jerusalém e o templo; começa o exílio de Judá.", ref: "2Rs 25" },
    { ano: 538, nome: "Ciro", texto: "Decreto de Ciro: os exilados podem voltar a Jerusalém.", ref: "Ed 1" },
    { ano: 5, nome: "Jesus", texto: "Nascimento de Jesus (data aproximada, entre 6 e 4 a.C.).", ref: "Mt 1–2; Lc 2" },
    { ano: -30, nome: "Cruz", texto: "Morte e ressurreição de Jesus e Pentecostes (c. 30 d.C.).", ref: "Mt 27–28; At 2" },
    { ano: -70, nome: "Templo", texto: "Tito destrói Jerusalém e o templo.", ref: "Mt 24:1-2" }
  ];

  var COLUNAS = [
    { id: "eras", nome: "Eras", cor: "era" },
    { id: "livros", nome: "Livros", cor: "livro" },
    { id: "reis", nome: "Terra prometida", cor: "terra" },
    { id: "potencias", nome: "Potências", cor: "potencia" }
  ];

  LT.ALTURA = ALTURA;
  LT.AT = AT;
  LT.AVALIACAO = AVALIACAO;
  LT.AXIS_FIM = AXIS_FIM;
  LT.AXIS_INICIO = AXIS_INICIO;
  LT.COLUNAS = COLUNAS;
  LT.ESCALA = ESCALA;
  LT.GRUPO = GRUPO;
  LT.JUNTA = JUNTA;
  LT.MARCOS = MARCOS;
  LT.MODOS = MODOS;
  LT.NT = NT;
  LT.REINO = REINO;
  LT.SEGMENTOS = SEGMENTOS;
  LT.TOP = TOP;
})();
