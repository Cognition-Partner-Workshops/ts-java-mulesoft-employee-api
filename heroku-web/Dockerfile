FROM node:18-alpine

WORKDIR /app

COPY package.json package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci --omit=dev; else npm install --omit=dev --no-audit --no-fund; fi

COPY . .

ENV NODE_ENV=production
ENV PORT=3000
EXPOSE 3000

USER node
CMD ["node", "server.js"]
