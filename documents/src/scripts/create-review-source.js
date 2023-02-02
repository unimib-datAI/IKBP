const fs = require('fs')

const ids = new Set(JSON.parse(fs.readFileSync('./ids.json')));
const allDocs = fs.readdirSync('./review-annotations/sources/gs_annotations_autolink');

let currentId = 1;
let folderNamesIndex = 0;
let folderNames = ['rpo_docs', 'christian_docs', 'marco_docs'];

allDocs.forEach((docId, index) => {
  const doc = JSON.parse(fs.readFileSync(`./review-annotations/sources/gs_annotations_autolink/${docId}`));
  if (ids.has(doc.name)) {
    if (!fs.existsSync(`./review-annotations/sources/${folderNames[folderNamesIndex]}`)) {
      fs.mkdirSync(`./review-annotations/sources/${folderNames[folderNamesIndex]}`, { recursive: true });
    }
    fs.writeFileSync(`./review-annotations/sources/${folderNames[folderNamesIndex]}/${currentId}.json`, JSON.stringify(doc))
    if (currentId % 10 === 0) {
      currentId = 1;
      folderNamesIndex += 1;
    } else {
      currentId += 1;
    }
  }
})