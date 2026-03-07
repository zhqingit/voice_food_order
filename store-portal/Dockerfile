FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json* ./
COPY packages/ ./packages/

# Build the vendored liquid-glass-react package.
# Copy the root tsconfig as the base config it extends (../../tsconfig.base.json),
# then build. The base config needs jsx: "react-jsx" for DTS generation.
COPY tsconfig.json /app/tsconfig.base.json
RUN cd packages/liquid-glass-react && npm install && npm run build

RUN npm install

COPY . .

EXPOSE 5174

CMD ["npm", "run", "dev"]
