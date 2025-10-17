/**
 * Simulate MongoDB collection
 */
export const DOCUMENTS = {
  1: {
    id: 1,
    title: 'Strage di Bologna',
    // qui ci sarà parte del contenuto inserito direttamente quando si aggiunge un documento al DB
    preview: '...',
    // percorso al contenuto completo del testo, verrà rimpiazzato con il teso al momento del findOne
    content: 'bologna.txt',
    // qui ci sarà direttemante una lista con tutte le annotazioni (al momento c'è un file separato)
    annotations: 'bologna.json' // [{ start, end, ... }, {...}]
  }
}