-- ===============================
-- CONFIGURACIÓN INICIAL DE BASE DE DATOS
-- ===============================
CREATE DATABASE motorush;
USE motorush;


SET FOREIGN_KEY_CHECKS = 1;

-- ===============================
-- TABLAS DE USUARIOS Y PERFILES
-- ===============================

-- Tabla principal de usuarios
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    last_name varchar(100) NOT NULL,
    gmail VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    rol ENUM('admin', 'cliente', 'motorizado') NOT NULL,
    photo VARCHAR(255) NOT NULL DEFAULT 'default.jpg',
    status ENUM('disponible', 'ocupado', 'activo', 'inactivo') NOT NULL DEFAULT 'activo'
);

-- Tabla de direcciones de usuarios
CREATE TABLE IF NOT EXISTS addresses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    address TEXT NOT NULL,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    lat DECIMAL(10, 8),
    lng DECIMAL(11, 8) NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Tabla para perfiles de usuario para recomendaciones
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id INT PRIMARY KEY,
    preferences JSON,
    feature_types JSON,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Tabla de suscripciones push
CREATE TABLE push_subscriptions (
    user_id INT NOT NULL,
    role VARCHAR(50) NOT NULL,
    endpoint VARCHAR(767) NOT NULL,  -- Cambiamos TEXT a VARCHAR con longitud definida
    p256dh TEXT NOT NULL,
    auth TEXT NOT NULL,
    PRIMARY KEY (user_id, endpoint),  -- Al ser VARCHAR ahora podemos usarlo en PRIMARY KEY
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ===============================
-- TABLAS DE CATÁLOGO DE PRODUCTOS
-- ===============================

-- Tabla de categorías de productos
CREATE TABLE categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    image_path VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Tabla de productos
CREATE TABLE products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    stock int NOT NULL,
    estado TINYINT(1) DEFAULT 1,
    image VARCHAR(255) NOT NULL,
    image2 VARCHAR(255) NOT NULL,
    image3 VARCHAR(255) NOT NULL,
    category_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

-- ===============================
-- TABLAS DE EVALUACIONES Y RESEÑAS
-- ===============================

-- Tabla de evaluaciones de productos
CREATE TABLE product_evaluations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    product_id INT NOT NULL,
    rating INT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

-- Tabla de reseñas
CREATE TABLE reviews (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    user_id INT NOT NULL,
    rating TINYINT NOT NULL,
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Tabla de evaluaciones generales
CREATE TABLE evaluations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    evaluation_name VARCHAR(255),
    evaluation_date DATE,
    user_id INT,
    rating INT,
    comment TEXT,
    order_id INT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- ===============================
-- TABLAS DE CARRITO Y PEDIDOS
-- ===============================

-- Tabla de carrito de compras
CREATE TABLE IF NOT EXISTS cart (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    UNIQUE KEY user_product (user_id, product_id)
);

-- Tabla de pedidos
CREATE TABLE orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    address_id INT NOT NULL,
    total_amount DECIMAL(10, 2) NOT NULL,
    payment_amount DECIMAL(10, 2) NOT NULL,
    payment_method VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pendiente',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    motorizado_id INT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    client_latitude DECIMAL(10, 8),
    client_longitude DECIMAL(11, 8),
    motorizado_latitude DECIMAL(10, 8),
    motorizado_longitude DECIMAL(11, 8),
    client_confirm_delivery BOOLEAN DEFAULT FALSE,
    motorizado_confirm_delivery BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (address_id) REFERENCES addresses(id),
    CONSTRAINT fk_motorizado FOREIGN KEY (motorizado_id) REFERENCES users(id)
);

-- Tabla de items de pedido
CREATE TABLE IF NOT EXISTS order_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- Tabla de asignación de motorizados a pedidos
CREATE TABLE order_assignments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    motorizado_id INT NOT NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (motorizado_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_assignment (order_id, motorizado_id)
);

-- ===============================
-- TABLAS PARA ANÁLISIS Y RECOMENDACIONES
-- ===============================

-- Tabla para seguimiento de productos vistos
CREATE TABLE IF NOT EXISTS product_views (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    product_id INT NOT NULL,
    viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    KEY idx_user_product (user_id, product_id),
    KEY idx_viewed_at (viewed_at)
);

-- Tabla para relaciones entre productos
CREATE TABLE IF NOT EXISTS product_relationships (
    id INT AUTO_INCREMENT PRIMARY KEY,
    source_product_id INT NOT NULL,
    related_product_id INT NOT NULL,
    relationship_strength INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (source_product_id) REFERENCES products(id) ON DELETE CASCADE,
    FOREIGN KEY (related_product_id) REFERENCES products(id) ON DELETE CASCADE,
    UNIQUE KEY uniq_product_relation (source_product_id, related_product_id)
);

-- Tabla para registrar cuando se recomienda un producto a un usuario
CREATE TABLE IF NOT EXISTS recommendation_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    product_id INT NOT NULL,
    recommended_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    clicked BOOLEAN DEFAULT FALSE,
    added_to_cart BOOLEAN DEFAULT FALSE,
    purchased BOOLEAN DEFAULT FALSE,
    INDEX (user_id, product_id),
    INDEX (recommended_at)
);

-- Tabla para almacenar modelos y parámetros de IA
CREATE TABLE IF NOT EXISTS ai_models (
    id INT AUTO_INCREMENT PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL,
    model_type VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    active BOOLEAN DEFAULT TRUE,
    parameters JSON,
    metrics JSON,
    INDEX (model_name, active)
);

-- ===============================
-- CONSULTAS DE SELECCIÓN
-- ===============================
-- SELECT * FROM users;
-- SELECT * FROM categories;

-- ===============================
-- COMANDOS DE LIMPIEZA DE TABLAS
-- ===============================
-- TRUNCATE TABLE categories;
-- TRUNCATE TABLE products;
-- TRUNCATE TABLE product_relationships;
-- TRUNCATE TABLE recommendation_logs;
-- TRUNCATE TABLE addresses;
-- TRUNCATE TABLE orders;
-- TRUNCATE TABLE order_items;