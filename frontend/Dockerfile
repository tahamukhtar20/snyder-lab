FROM node:20-alpine

WORKDIR /app

COPY . .

EXPOSE 5173

RUN npm install

CMD [ "npm", "run", "dev" ]