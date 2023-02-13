const fs = require('fs')

function isNumber(value) {
  if (typeof value === "string") {
    return !isNaN(value);
  }
}

const commandsFunctions = {
  time: (folders) => {
    const data = []
    folders.forEach((folder) => {
      const files = fs.readdirSync(`${path}/${folder}`);

      files.forEach((file) => {
        const doc = JSON.parse(fs.readFileSync(`${path}/${folder}/${file}`));
        const annSet = Object.values(doc.annotation_sets)[0];
        let totalTime = 0;
        const { avgReviewTime } = doc.features;

        annSet.annotations.forEach((ann) => {
          const annTime = ann.features.review_time || 0;
          totalTime += annTime;
        })
        data.push({
          id: doc.name,
          total_time_minutes: totalTime / 60,
          total_time_seconds: totalTime,
          avg_time_per_question_seconds: avgReviewTime
        })

      })
    })

    console.table(data);
    const totalTimeAnnotation = data.reduce((acc, row) => acc + row.total_time_seconds, 0);
    console.log('Avarage annotation time per document: ', totalTimeAnnotation / data.length / 60)
  },
  links: (folders) => {
    let links = {
      wikipedia: [],
      nil: [],
      skip: []
    }
    folders.forEach((folder) => {
      const files = fs.readdirSync(`${path}/${folder}`);

      files.forEach((file) => {
        const doc = JSON.parse(fs.readFileSync(`${path}/${folder}/${file}`));
        const annSet = Object.values(doc.annotation_sets)[0];

        links = annSet.annotations.reduce((acc, ann) => {
          const { url } = ann.features;

          if (url.includes('wikipedia')) {
            acc.wikipedia.push(url);
          } else if (!url) {
            acc.skip.push(url);
          } else {
            acc.nil.push(url);
          }
          return acc;

        }, links);
      })
    })

    const getTotal = (links) => {
      return Object.values(links).reduce((acc, linkGroup) => acc + linkGroup.length, 0);
    }

    const getUniqueLinks = (links) => {
      let uniqueLinks = {
        wikipedia: [],
        nil: [],
        skip: []
      }
      for (const key in links) {
        uniqueLinks[key] = Array.from(new Set(links[key]));
      }
      return uniqueLinks;
    }

    const uniqueLinks = getUniqueLinks(links);

    console.log('Total mentions: ', getTotal(links))
    console.log('Total wikipedia links: ', links.wikipedia.length)
    console.log('Total nil links: ', links.nil.length)
    console.log('Total skipped mentions: ', links.skip.length)
    console.log('Total unique clusters: ', getTotal(uniqueLinks))
    console.log('Wikipedia unique clusters: ', uniqueLinks.wikipedia.length)
    console.log('Nil unique clusters: ', uniqueLinks.nil.length)

  }
}

const commands = new Set(Object.keys(commandsFunctions));

const parseArgs = () => {
  const argsList = process.argv.slice(2);
  const args = new Map();


  for (let i = 0; i < argsList.length; i++) {
    if (i === 0) {
      const arg = argsList[i];
      if (!commands.has(arg)) {
        throw new Error('Invalid command');
      }
      args.set('cmd', arg);
    } else {
      if (argsList[i].startsWith('-')) {
        const arg = argsList[i].slice('-')[1];
        let value = argsList[i + 1];

        if (arg === 'e') {
          value = value.split(',')
        } else if (isNumber(value)) {
          value = Number(value);
        }
        args.set(arg, value);
      }
    }
  }

  return args;
}

const args = parseArgs();

const cmd = args.get('cmd');
const path = args.get('p');
const exclude = new Set(args.get('e'));
const folders = fs.readdirSync(path).filter((folder) => !exclude.has(folder));


commandsFunctions[cmd](folders);






