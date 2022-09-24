# Documents microservice

This service is responsible to expose an API to perform operations on documents, e.g., get documents, get annotations, edit annotations.

## Structure

```
.
├── _collections
│   |   // used to simulate a mongoDB collection. Once mongoDB is setup this can be removed
│   └── document.js
├── _files
│   | // used to simulate the content of a mongoDB document
|   | // representing a document and its annotations. Once mongoDB is setup this can be removed
│   ├── text.txt // textual content of a document
│   └── text.json // annotations of a document
├── api
│   // routes of the api
├── controllers
│   // controllers used in the routes
├── loaders
│   // a loader is part of the initial configuration of the server (express, mongodb, external services, ...)
├── utils
└── app.js
```

## Run locally

Be sure to have `pnpm` and `node` installed. If you do not you can refer to this: https://pnpm.io/it/installation.

Once you have all requirements you can install the libraries required by the application:

```
pnpm install
```

Start the server:

```
pnpm run dev
```
