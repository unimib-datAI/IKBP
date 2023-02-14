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

    const getTotal = (linkGroups) => {
      return Object.values(linkGroups).reduce((acc, linkGroup) => acc + linkGroup.length, 0);
    }

    const getTotalStat = (documentStats, column) => {
      return documentStats.reduce((acc, stats) => acc + stats[column], 0);
    }

    const getMeanStat = (documentStats, column) => {
      return documentStats.reduce((acc, stats) => acc + stats[column], 0) / documentStats.length;
    }

    const getUniqueLinks = (linkGroups) => {
      let uniqueLinks = {
        wikipedia: [],
        nil: [],
        skip: []
      }
      for (const key in linkGroups) {
        uniqueLinks[key] = Array.from(new Set(linkGroups[key]));
      }
      return uniqueLinks;
    }

    let linksStats = [];

    folders.forEach((folder) => {
      const files = fs.readdirSync(`${path}/${folder}`);

      files.forEach((file) => {
        const doc = JSON.parse(fs.readFileSync(`${path}/${folder}/${file}`));
        const annSet = Object.values(doc.annotation_sets)[0];

        const linkGroups = annSet.annotations.reduce((acc, ann) => {
          const { url } = ann.features;

          if (url.includes('wikipedia')) {
            acc.wikipedia.push(url);
          } else if (!url) {
            acc.skip.push(url);
          } else {
            acc.nil.push(url);
          }
          return acc;

        }, { wikipedia: [], nil: [], skip: [] });

        const uniqueLinks = getUniqueLinks(linkGroups);

        linksStats.push({
          id: doc.name,
          n_mentions: getTotal(linkGroups),
          total_wikipedia_links: linkGroups.wikipedia.length,
          total_nil_links: linkGroups.nil.length,
          total_skipped_mentions: linkGroups.skip.length,
          total_unique_clusters: getTotal(uniqueLinks),
          wikipedia_unique_clusters: uniqueLinks.wikipedia.length,
          nil_unique_clusters: uniqueLinks.nil.length
        })
      })
    })


    console.table(linksStats);
    console.log('\n------------------------AVARAGE STATS PER DOCUMENT------------------------\n')
    console.log('Avarage mentions per document: ', getMeanStat(linksStats, 'n_mentions'))
    console.log('Avarage total wikipedia links per document: ', getMeanStat(linksStats, 'total_wikipedia_links'))
    console.log('Avarage total nil links per document: ', getMeanStat(linksStats, 'total_nil_links'))
    console.log('Avarage total skipped mentions per document: ', getMeanStat(linksStats, 'total_skipped_mentions'))
    console.log('Avarage unique clusters per document: ', getMeanStat(linksStats, 'total_unique_clusters'))
    console.log('Avarage wikipedia unique clusters per document: ', getMeanStat(linksStats, 'wikipedia_unique_clusters'))
    console.log('Avarage nil unique clusters per document: ', getMeanStat(linksStats, 'nil_unique_clusters'))
    console.log('\n------------------------TOTAL STATS------------------------\n')
    console.log('Total mentions: ', getTotalStat(linksStats, 'n_mentions'))
    console.log('Total wikipedia links: ', getTotalStat(linksStats, 'total_wikipedia_links'))
    console.log('Total nil links: ', getTotalStat(linksStats, 'total_nil_links'))
    console.log('Total skipped mentions: ', getTotalStat(linksStats, 'total_skipped_mentions'))
    console.log('Total unique clusters: ', getTotalStat(linksStats, 'total_unique_clusters'))
    console.log('Wikipedia unique clusters: ', getTotalStat(linksStats, 'wikipedia_unique_clusters'))
    console.log('Nil unique clusters: ', getTotalStat(linksStats, 'nil_unique_clusters'))
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






