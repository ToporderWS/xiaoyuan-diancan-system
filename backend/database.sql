-- =============================================================================
--  《校园点餐管理系统》数据库初始化脚本
--  数据库：MySQL 8.0    字符集：utf8mb4    存储引擎：InnoDB
--  说明：8 张业务表结构为【绝对冻结】，仅允许附加 PRIMARY KEY / UNIQUE /
--        INDEX / FOREIGN KEY / CHECK 约束，不得新增业务字段、删除字段或改字段名。
--  执行方式：
--        mysql -u root -p < database.sql
-- =============================================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- -----------------------------------------------------------------------------
-- 0. 创建数据库
-- -----------------------------------------------------------------------------
CREATE DATABASE IF NOT EXISTS `campus_order`
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_general_ci;

USE `campus_order`;

-- -----------------------------------------------------------------------------
-- 1. 清理旧表（按外键依赖倒序）
-- -----------------------------------------------------------------------------
DROP TABLE IF EXISTS `order_item`;
DROP TABLE IF EXISTS `cart`;
DROP TABLE IF EXISTS `orders`;
DROP TABLE IF EXISTS `food`;
DROP TABLE IF EXISTS `food_category`;
DROP TABLE IF EXISTS `notice`;
DROP TABLE IF EXISTS `admin_user`;
DROP TABLE IF EXISTS `users`;

-- -----------------------------------------------------------------------------
-- 2. users —— 学生用户表
--    role 字段【禁止】存在于此表，角色仅存于 JWT Payload
-- -----------------------------------------------------------------------------
CREATE TABLE `users` (
    `id`            INT           NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `phone`         VARCHAR(20)   NOT NULL                COMMENT '手机号（登录账号）',
    `password_hash` VARCHAR(255)  NOT NULL                COMMENT '密码哈希（Werkzeug）',
    `nickname`      VARCHAR(50)   NOT NULL DEFAULT ''     COMMENT '昵称',
    `avatar`        VARCHAR(255)  NOT NULL DEFAULT 'default_user.jpg' COMMENT '头像文件名（仅文件名）',
    `student_no`    VARCHAR(30)   NOT NULL DEFAULT ''     COMMENT '学号',
    `dormitory`     VARCHAR(100)  NOT NULL DEFAULT ''     COMMENT '宿舍（默认收货地址）',
    `created_at`    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_users_phone` (`phone`),
    KEY `idx_users_nickname` (`nickname`),
    KEY `idx_users_created_at` (`created_at`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '学生用户表';

-- -----------------------------------------------------------------------------
-- 3. admin_user —— 管理员表
-- -----------------------------------------------------------------------------
CREATE TABLE `admin_user` (
    `id`            INT           NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `admin_name`    VARCHAR(50)   NOT NULL                COMMENT '管理员账号',
    `password_hash` VARCHAR(255)  NOT NULL                COMMENT '密码哈希（Werkzeug）',
    `real_name`     VARCHAR(50)   NOT NULL DEFAULT ''     COMMENT '真实姓名',
    `avatar`        VARCHAR(255)  NOT NULL DEFAULT 'default_user.jpg' COMMENT '头像文件名（仅文件名）',
    `created_at`    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_admin_user_admin_name` (`admin_name`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '管理员表';

-- -----------------------------------------------------------------------------
-- 4. food_category —— 菜品分类表
-- -----------------------------------------------------------------------------
CREATE TABLE `food_category` (
    `id`         INT         NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `cat_name`   VARCHAR(50) NOT NULL                COMMENT '分类名称',
    `sort`       INT         NOT NULL DEFAULT 0      COMMENT '排序值（升序）',
    `is_show`    TINYINT(1)  NOT NULL DEFAULT 1      COMMENT '是否启用：0禁用 1启用',
    `created_at` DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_food_category_cat_name` (`cat_name`),
    KEY `idx_food_category_sort` (`sort`, `is_show`),
    CONSTRAINT `ck_food_category_is_show` CHECK (`is_show` IN (0, 1))
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '菜品分类表';

-- -----------------------------------------------------------------------------
-- 5. food —— 菜品表
-- -----------------------------------------------------------------------------
CREATE TABLE `food` (
    `id`          INT            NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `cat_id`      INT            NOT NULL                COMMENT '所属分类ID',
    `food_name`   VARCHAR(100)   NOT NULL                COMMENT '菜品名称',
    `price`       DECIMAL(10, 2) NOT NULL DEFAULT 0.00   COMMENT '单价（元）',
    `stock`       INT            NOT NULL DEFAULT 0      COMMENT '库存',
    `sales`       INT            NOT NULL DEFAULT 0      COMMENT '销量',
    `food_img`    VARCHAR(255)   NOT NULL DEFAULT ''     COMMENT '菜品图片文件名（仅文件名）',
    `description` TEXT                                   NULL COMMENT '菜品描述',
    `is_sale`     TINYINT(1)     NOT NULL DEFAULT 1      COMMENT '是否上架：0下架 1上架',
    `created_at`  DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    KEY `idx_food_cat_id` (`cat_id`),
    KEY `idx_food_is_sale` (`is_sale`),
    KEY `idx_food_food_name` (`food_name`),
    CONSTRAINT `fk_food_category` FOREIGN KEY (`cat_id`) REFERENCES `food_category` (`id`)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT `ck_food_price` CHECK (`price` >= 0),
    CONSTRAINT `ck_food_stock` CHECK (`stock` >= 0),
    CONSTRAINT `ck_food_sales` CHECK (`sales` >= 0),
    CONSTRAINT `ck_food_is_sale` CHECK (`is_sale` IN (0, 1))
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '菜品表';

-- -----------------------------------------------------------------------------
-- 6. orders —— 订单表
--    order_status：0待支付 1待接单 2已接单/配送中 3已完成 4已取消
-- -----------------------------------------------------------------------------
CREATE TABLE `orders` (
    `id`              INT            NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `order_no`        VARCHAR(50)    NOT NULL                COMMENT '订单号',
    `user_id`         INT            NOT NULL                COMMENT '下单学生ID',
    `total_price`     DECIMAL(10, 2) NOT NULL DEFAULT 0.00   COMMENT '订单总金额',
    `receive_address` VARCHAR(120)   NOT NULL DEFAULT ''     COMMENT '收货地址',
    `remark`          VARCHAR(200)   NOT NULL DEFAULT ''     COMMENT '备注',
    `order_status`    TINYINT(1)     NOT NULL DEFAULT 0      COMMENT '订单状态',
    `pay_time`        DATETIME                               NULL COMMENT '支付时间',
    `finish_time`     DATETIME                               NULL COMMENT '完成时间',
    `created_at`      DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_orders_order_no` (`order_no`),
    KEY `idx_orders_user_id` (`user_id`),
    KEY `idx_orders_status_created` (`order_status`, `created_at`),
    KEY `idx_orders_created_at` (`created_at`),
    CONSTRAINT `fk_orders_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT `ck_orders_status` CHECK (`order_status` IN (0, 1, 2, 3, 4))
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '订单表';

-- -----------------------------------------------------------------------------
-- 7. order_item —— 订单明细快照表
-- -----------------------------------------------------------------------------
CREATE TABLE `order_item` (
    `id`         INT            NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `order_id`   INT            NOT NULL                COMMENT '订单ID',
    `food_id`    INT            NOT NULL                COMMENT '菜品ID',
    `food_name`  VARCHAR(100)   NOT NULL                COMMENT '菜品名称快照',
    `food_price` DECIMAL(10, 2) NOT NULL DEFAULT 0.00   COMMENT '菜品单价快照',
    `count`      INT            NOT NULL DEFAULT 1      COMMENT '购买数量',
    `created_at` DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    KEY `idx_order_item_order_id` (`order_id`),
    KEY `idx_order_item_food_id` (`food_id`),
    CONSTRAINT `fk_order_item_order` FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `ck_order_item_count` CHECK (`count` > 0),
    CONSTRAINT `ck_order_item_price` CHECK (`food_price` >= 0)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '订单明细表';

-- -----------------------------------------------------------------------------
-- 8. cart —— 购物车表（实时读写 MySQL）
-- -----------------------------------------------------------------------------
CREATE TABLE `cart` (
    `id`         INT      NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `user_id`    INT      NOT NULL                COMMENT '学生ID',
    `food_id`    INT      NOT NULL                COMMENT '菜品ID',
    `count`      INT      NOT NULL DEFAULT 1      COMMENT '数量',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_cart_user_food` (`user_id`, `food_id`),
    KEY `idx_cart_food_id` (`food_id`),
    CONSTRAINT `fk_cart_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `fk_cart_food` FOREIGN KEY (`food_id`) REFERENCES `food` (`id`)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `ck_cart_count` CHECK (`count` > 0)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '购物车表';

-- -----------------------------------------------------------------------------
-- 9. notice —— 公告表
-- -----------------------------------------------------------------------------
CREATE TABLE `notice` (
    `id`           INT          NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `title`        VARCHAR(200) NOT NULL                COMMENT '公告标题',
    `content`      TEXT                                 NULL COMMENT '公告内容',
    `publish_time` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '发布时间',
    `is_show`      TINYINT(1)   NOT NULL DEFAULT 1      COMMENT '是否显示：0隐藏 1显示',
    PRIMARY KEY (`id`),
    KEY `idx_notice_show_time` (`is_show`, `publish_time`),
    CONSTRAINT `ck_notice_is_show` CHECK (`is_show` IN (0, 1))
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '公告表';

-- -----------------------------------------------------------------------------
-- 10. 初始化数据：5 个菜品分类
-- -----------------------------------------------------------------------------
INSERT INTO `food_category` (`cat_name`, `sort`, `is_show`) VALUES
    ('早餐', 1, 1),
    ('快餐', 2, 1),
    ('面食', 3, 1),
    ('饮品', 4, 1),
    ('小吃', 5, 1);

SET FOREIGN_KEY_CHECKS = 1;

-- =============================================================================
-- 建库完成。
-- 管理员账号请执行：python scripts/init_admin.py
-- 说明：本脚本不写入任何管理员明文密码。
-- =============================================================================
