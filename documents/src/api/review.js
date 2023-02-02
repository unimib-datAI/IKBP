import { json, Router } from 'express';
import { asyncRoute } from '../utils/async-route';
import { readdir, access, mkdir, readFile, writeFile } from 'fs/promises'
import { HTTPError, HTTP_ERROR_CODES } from '../utils/http-error';

const route = Router();

const readDocument = async (path) => {
  const doc = JSON.parse(await readFile(path));
  const annSet = Object.keys(doc.annotation_sets)[0];

  if (!annSet) {
    return doc;
  }

  const annotations = doc.annotation_sets[annSet].annotations.map((ann) => {
    if (!ann?.features?.linking) {
      return ann
    }
    const { encoding: _, ...linking } = ann.features.linking;

    return {
      ...ann,
      features: {
        ...ann.features,
        linking: linking
      }
    }
  })

  return {
    ...doc,
    annotation_sets: {
      ...doc.annotation_sets,
      [annSet]: {
        ...doc.annotation_sets[annSet],
        annotations
      }
    }
  }
}

const exists = async (path) => {
  try {
    await access(path)
    return true;
  } catch (err) {
    return false;
  }
}

export default (app) => {
  // route base root
  app.use('/review', route);

  route.get('/source', asyncRoute(async (req, res) => {

    let dirs = await readdir('./review-annotations/sources');

    dirs = await Promise.all(dirs.map(async (dir) => {
      const sourceFiles = await readdir(`./review-annotations/sources/${dir}`);

      if (!(await exists(`./review-annotations/destinations/${dir}`))) {
        await mkdir(`./review-annotations/destinations/${dir}`)
      }

      const destFiles = await readdir(`./review-annotations/destinations/${dir}`);

      const total = sourceFiles.length;
      const done = destFiles.length;

      return {
        id: dir,
        name: dir.split('_').join(' '),
        total,
        done
      }

    }));

    return res.json({
      sources: dirs
    })
  }));

  route.get('/source/:id', asyncRoute(async (req, res, next) => {
    const { id } = req.params;

    try {
      const sourcePath = `./review-annotations/sources/${id}`;
      const destPath = `./review-annotations/destinations/${id}`;

      const sourceFiles = (await readdir(sourcePath)).sort((a, b) => {
        const first = Number(a.split('.')[0]);
        const second = Number(b.split('.')[0]);
        return first < second ? -1 : 1;
      });
      const destFiles = (await readdir(destPath)).sort((a, b) => {
        const first = Number(a.split('.')[0]);
        const second = Number(b.split('.')[0]);
        return first < second ? -1 : 1;
      });

      const total = sourceFiles.length;
      const doneIds = new Set(destFiles.map((file) => file.split('.')[0]));

      const files = await Promise.all(sourceFiles.map(async (file) => {
        const doc = JSON.parse(await readFile(`${sourcePath}/${file}`));
        const id = file.split('.')[0];
        const annSet = Object.values(doc.annotation_sets)[0];
        return {
          id,
          name: doc.name,
          done: doneIds.has(id),
          nAnnotations: !annSet ? 0 : annSet.annotations.length
        }
      }));

      return res.json({
        name: id.split('_').map((str) => str[0].toUpperCase() + str.substr(1)).join(' '),
        total,
        doneIds: Array.from(doneIds),
        docs: files
      })

    } catch (err) {
      console.log(err);
      return next(new HTTPError({
        code: HTTP_ERROR_CODES.NOT_FOUND,
        message: `Source with id '${id}' not found`
      }))
    }
  }))

  route.get('/source/:sourceId/doc/:docId', asyncRoute(async (req, res, next) => {
    const { sourceId, docId } = req.params;
    console.log(req.params);

    const initialPage = docId || 1;
    const index = initialPage - 1;

    try {
      const sourcePath = `./review-annotations/sources/${sourceId}`;
      const destPath = `./review-annotations/destinations/${sourceId}`;
      const sourceFiles = (await readdir(sourcePath)).sort((a, b) => {
        const first = Number(a.split('.')[0]);
        const second = Number(b.split('.')[0]);
        return first < second ? -1 : 1;
      });
      const destFiles = await readdir(destPath);

      if (initialPage < 0 || initialPage > sourceFiles.length) {
        return next(new HTTPError({
          code: HTTP_ERROR_CODES.NOT_FOUND,
          message: `Document with id '${initialPage}' not found`
        }))
      }

      const docDone = new Set(destFiles.map((file) => file.split('.')[0])).has(docId);
      const doc = await readDocument(docDone ? `${destPath}/${docId}.json` : `${sourcePath}/${sourceFiles[index]}`);

      return res.json({
        docId,
        hasNextPage: initialPage > 0 && initialPage < sourceFiles.length,
        hasPreviousPage: initialPage <= sourceFiles.length && initialPage > 1,
        currentDocument: doc
      })

    } catch (err) {
      console.log(err);
      return next(new HTTPError({
        code: HTTP_ERROR_CODES.NOT_FOUND,
        message: `Source with id '${sourceId}' not found`
      }))
    }
  }))

  route.post('/source/:sourceId/doc/:docId', asyncRoute(async (req, res, next) => {
    const { sourceId, docId } = req.params;
    const { document } = req.body;

    const destPath = `./review-annotations/destinations/${sourceId}/${docId}.json`;
    try {
      await writeFile(destPath, JSON.stringify(document));
    } catch (err) {
      return next(new HTTPError({
        code: HTTP_ERROR_CODES.BAD_REQUEST,
        message: `Invalid file path`
      }))
    }
    return res.json({
      sourceId,
      docId
    })
  }))
};