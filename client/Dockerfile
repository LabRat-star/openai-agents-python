FROM node:18-alpine
WORKDIR /app
COPY client/package.json /app/package.json
RUN npm install --legacy-peer-deps
COPY client /app
RUN npm run build
EXPOSE 3000
CMD ["npm", "run", "start"]
