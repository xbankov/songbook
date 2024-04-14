# Use Node.js LTS version as base image
FROM node:lts

# Set working directory inside the container
WORKDIR /app

# Copy package.json and package-lock.json files to the working directory
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy all files from the current directory to the working directory inside the container
COPY . .

# Expose port 8080 for development server
EXPOSE 8080

# Run Vue development server
CMD ["npm", "run", "serve"]
