# Frontend image - runs the CRA dev server (matches the rest of this stack,
# which is a local-dev setup, not a hardened prod deploy). For a real
# production image, replace CMD with a multi-stage `npm run build` +
# static file server (e.g. `serve -s build`) instead.
FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

EXPOSE 3000

# Polling avoids missed file-change events on some bind-mount/VM setups.
ENV CHOKIDAR_USEPOLLING=true

CMD ["npm", "start"]
