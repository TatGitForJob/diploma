FROM node:18-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm install vite

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host"]
