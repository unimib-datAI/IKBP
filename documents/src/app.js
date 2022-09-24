import 'dotenv/config'
import { startServer } from './loaders'

const server = startServer(({ PORT }) => {
  console.log(`👾 Server running at http://localhost:${PORT} 👾`)
})

