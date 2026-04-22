FROM nginx:1.27-alpine

RUN rm /etc/nginx/conf.d/default.conf

COPY nginx.conf.template /etc/nginx/templates/default.conf.template

COPY index.html /usr/share/nginx/html/
COPY app.js     /usr/share/nginx/html/
COPY app.css    /usr/share/nginx/html/

ENV BACKEND_HOST=backend

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -q --spider http://localhost/ || exit 1
