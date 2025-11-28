#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Restaure les styles inline dans les templates sans doublons.
Chaque template reçoit UNIQUEMENT les styles qu'il utilise.
"""

TEMPLATE_STYLES = {
    'base.html': '''
    <style>
        /* NAVIGATION */
        nav {
            background: linear-gradient(90deg, #1E3A8A, #3B65C4);
            padding: 15px 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: sticky;
            top: 0;
            z-index: 1000;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        }
        
        nav .logo {
            color: white;
            font-size: 24px;
            font-weight: 600;
            letter-spacing: 1px;
        }
        
        nav ul {
            list-style: none;
            margin: 0;
            padding: 0;
            display: flex;
            gap: 30px;
        }
        
        nav a {
            color: white;
            text-decoration: none;
            font-weight: 400;
            font-size: 16px;
            padding: 5px 10px;
            transition: all 0.3s;
        }
        
        nav a:hover {
            background: rgba(255, 255, 255, 0.2);
            color: #ffffff;
            padding: 5px 10px;
            border-radius: 5px;
            transition: background 0.3s;
        }
        
        .hamburger {
            display: none;
            flex-direction: column;
            cursor: pointer;
        }
        
        .hamburger span {
            height: 3px;
            width: 28px;
            background: white;
            margin: 4px 0;
            border-radius: 3px;
            transition: 0.3s;
        }
        
        @media (max-width: 768px) {
            nav ul {
                position: absolute;
                top: 70px;
                right: 0;
                width: 220px;
                background: linear-gradient(90deg, #1E3A8A, #3B65C4);
                padding: 20px;
                flex-direction: column;
                text-align: right;
                gap: 20px;
                display: none;
                box-shadow: -5px 5px 15px rgba(0,0,0,0.2);
                border-radius: 0 0 0 10px;
            }
            nav ul.show {
                display: flex;
            }
            .hamburger {
                display: flex;
            }
        }
        
        /* USER MENU */
        .user-menu {
            position: relative;
        }
        
        .user-menu-content {
            display: none;
            position: absolute;
            top: 100%;
            right: 0;
            background: white;
            border-radius: 10px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.15);
            padding: 20px;
            min-width: 300px;
            z-index: 999;
        }
        
        .user-menu-content.show {
            display: flex;
            flex-direction: column;
            gap: 15px;
        }
        
        .user-menu-links {
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        
        .user-menu-links a {
            color: #1E3A8A;
            text-decoration: none;
            padding: 8px 0;
            border-bottom: 1px solid #f0f0f0;
        }
        
        .user-menu-links a:last-child {
            border-bottom: none;
        }
        
        .user-menu-section-title {
            font-weight: 700;
            color: #1E3A8A;
            margin-top: 10px;
            font-size: 14px;
        }
        
        .cart-preview {
            border-top: 1px solid #f0f0f0;
            padding-top: 15px;
        }
        
        .cart-item {
            display: flex;
            gap: 10px;
            align-items: center;
        }
        
        .cart-item img {
            width: 40px;
            height: 40px;
            object-fit: cover;
            border-radius: 5px;
        }
        
        .cart-item-details {
            flex: 1;
            font-size: 12px;
        }
        
        .cart-item-details p {
            margin: 0;
        }
        
        .mega-menu-cart-btn {
            display: inline-block;
            padding: 10px 15px;
            background: linear-gradient(90deg, #1E3A8A, #3B65C4);
            color: white;
            border-radius: 8px;
            text-decoration: none;
            text-align: center;
            margin-top: 10px;
        }
        
        /* FLASH MESSAGES */
        .flash-container {
            position: fixed;
            top: 70px;
            right: 20px;
            z-index: 2000;
            max-width: 400px;
        }
        
        .flash-message {
            background: #4CAF50;
            color: white;
            padding: 15px 20px;
            border-radius: 8px;
            margin-bottom: 10px;
            box-shadow: 0 3px 10px rgba(0,0,0,0.2);
            animation: slideIn 0.3s ease-out;
        }
        
        .flash-message.hide {
            animation: slideOut 0.3s ease-out forwards;
        }
        
        @keyframes slideIn {
            from {
                transform: translateX(400px);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        @keyframes slideOut {
            to {
                transform: translateX(400px);
                opacity: 0;
            }
        }
    </style>
    ''',
    
    'index.html': '''
    <style>
        /* GLOBAL */
        body {
            margin: 0;
            font-family: "Poppins", sans-serif;
            background: linear-gradient(to bottom, #e0f2ff, #c0d9ff);
            color: #222;
        }
        
        /* HERO SECTION */
        .hero {
            width: 98%;
            margin: 0 auto;
            height: 65vh;
            position: relative;
            border-radius: 25px;
            overflow: hidden;
            box-shadow: 0 10px 25px rgba(0,0,0,0.25);
        }
        
        .hero-media {
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: block;
        }
        
        .hero-overlay {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(to bottom, rgba(0,0,50,0.2), rgba(0,0,80,0.6));
            display: flex;
            justify-content: center;
            align-items: center;
            text-align: center;
            padding: 30px;
            color: white;
        }
        
        .hero-overlay h1 {
            font-size: 48px;
            font-weight: 700;
            margin: 0;
        }
        
        .hero-overlay p {
            font-size: 20px;
            margin-top: 10px;
            opacity: 0.9;
        }
        
        @media (max-width: 768px) {
            .hero {
                height: 50vh;
            }
            .hero-overlay h1 {
                font-size: 32px;
            }
            .hero-overlay p {
                font-size: 16px;
            }
        }
        
        /* SECTIONS */
        .section {
            padding: 60px 20px;
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .section h2 {
            font-size: 36px;
            font-weight: 700;
            text-align: center;
            margin-bottom: 40px;
            color: #1E3A8A;
        }
        
        .section p {
            font-size: 18px;
            line-height: 1.6;
            text-align: center;
            margin-bottom: 20px;
        }
        
        /* GALLERY */
        .latest-gallery {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 25px;
            margin-top: 20px;
        }
        
        .latest-artwork {
            position: relative;
            background: #ffffff;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
            transition: transform 0.3s, box-shadow 0.3s;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        
        .latest-artwork:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 25px rgba(0,0,0,0.15);
        }
        
        .latest-artwork .badge {
            position: absolute;
            top: 10px;
            left: 10px;
            background: linear-gradient(90deg, #FF7F50, #FF4500);
            color: white;
            font-size: 12px;
            font-weight: 700;
            padding: 5px 10px;
            border-radius: 20px;
            text-transform: uppercase;
            z-index: 10;
        }
        
        .latest-artwork img {
            width: 100%;
            height: 280px;
            object-fit: cover;
        }
        
        .latest-artwork .info {
            padding: 15px;
            display: flex;
            flex-direction: column;
            gap: 8px;
            text-align: center;
        }
        
        .latest-artwork h3 {
            margin: 0;
            font-size: 18px;
            font-weight: 700;
            color: #1E3A8A;
        }
        
        .latest-artwork p {
            margin: 0;
            font-weight: 600;
            color: #333;
        }
        
        .latest-artwork button {
            margin-top: 10px;
            padding: 10px 15px;
            background: linear-gradient(90deg, #1E3A8A, #3B65C4);
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            transition: background 0.3s;
        }
        
        .latest-artwork button:hover {
            background: linear-gradient(90deg, #3B65C4, #1E3A8A);
        }
        
        .artwork-image-wrapper {
            position: relative;
            width: 100%;
            height: 280px;
            overflow: hidden;
        }
        
        .artwork-image-wrapper img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        
        .favorite-btn {
            position: absolute;
            top: 10px;
            right: 10px;
            font-size: 24px;
            cursor: pointer;
            background: rgba(255,255,255,0.8);
            border-radius: 50%;
            width: 40px;
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            text-decoration: none;
            transition: background 0.3s;
        }
        
        .favorite-btn:hover {
            background: rgba(255,255,255,1);
        }
        
        /* ABOUT SECTION */
        .about {
            margin-top: 50px;
        }
        
        .about-container {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 20px;
            justify-content: center;
        }
        
        .about-container img {
            width: 300px;
            max-width: 100%;
            height: auto;
            border-radius: 15px;
            object-fit: cover;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            transition: transform 0.3s, box-shadow 0.3s;
        }
        
        .about-container img:hover {
            transform: scale(1.05);
            box-shadow: 0 10px 25px rgba(0,0,0,0.2);
        }
        
        .about-container p {
            max-width: 600px;
            font-size: 16px;
            color: #333;
            line-height: 1.6;
            text-align: left;
        }
        
        @media (max-width: 768px) {
            .latest-gallery {
                grid-template-columns: 1fr;
            }
            .about-container {
                flex-direction: column;
                text-align: center;
            }
            .about-container p {
                text-align: center;
            }
        }
    </style>
    ''',

    'checkout.html': '''
    <style>
        .checkout-section {
            padding: 60px 20px;
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .checkout-grid {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 20px;
        }
        
        .checkout-cart, .checkout-form {
            background: #ffffff;
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        
        .checkout-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 15px;
        }
        
        .checkout-item img {
            width: 80px;
            height: 80px;
            object-fit: cover;
            border-radius: 10px;
            margin-right: 10px;
        }
        
        .checkout-info {
            display: flex;
            flex-direction: column;
            flex: 1;
        }
        
        .checkout-info .name {
            font-weight: 700;
            color: #1E3A8A;
        }
        
        .checkout-info .price {
            font-weight: 600;
            color: #333;
        }
        
        .checkout-info .quantity {
            font-size: 14px;
            color: #555;
        }
        
        .checkout-total {
            margin-top: 20px;
            font-size: 18px;
            font-weight: 700;
            text-align: right;
            color: #1E3A8A;
        }
        
        .checkout-form label {
            display: block;
            margin: 10px 0 5px;
            font-weight: 600;
        }
        
        .checkout-form input,
        .checkout-form textarea {
            width: 100%;
            padding: 10px;
            border-radius: 8px;
            border: 1px solid #ccc;
            margin-bottom: 10px;
            box-sizing: border-box;
        }
        
        .checkout-form button {
            width: 100%;
            padding: 12px;
            background: linear-gradient(90deg, #1E3A8A, #3B65C4);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            transition: background 0.3s;
        }
        
        .checkout-form button:hover {
            background: linear-gradient(90deg, #3B65C4, #1E3A8A);
        }
        
        @media (max-width: 768px) {
            .checkout-grid {
                grid-template-columns: 1fr;
            }
            .checkout-item {
                flex-direction: column;
                align-items: flex-start;
            }
            .checkout-info {
                margin-top: 10px;
            }
        }
    </style>
    ''',

    'cart.html': '''
    <style>
        .cart-section {
            padding: 60px 20px;
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .cart-section__container {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 20px;
        }
        
        .cart-section__items {
            display: grid;
            grid-template-columns: 1fr;
            gap: 20px;
        }
        
        .cart-section__item {
            position: relative;
            background: #ffffff;
            border-radius: 15px;
            overflow: hidden;
            display: flex;
            gap: 15px;
            align-items: center;
            padding: 10px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        
        .cart-section__item img {
            width: 120px;
            height: 120px;
            object-fit: cover;
            border-radius: 10px;
        }
        
        .cart-section__info {
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        
        .cart-section__header {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .cart-section__header h3 {
            margin: 0;
            font-size: 16px;
            font-weight: 700;
            color: #1E3A8A;
        }
        
        .cart-section__price {
            font-weight: 600;
            color: #333;
        }
        
        .cart-section__quantity-controls {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-top: 5px;
        }
        
        .cart-section__qty-btn {
            display: inline-block;
            width: 28px;
            height: 28px;
            text-align: center;
            line-height: 28px;
            background: linear-gradient(90deg, #1E3A8A, #3B65C4);
            color: white;
            border-radius: 50%;
            font-weight: bold;
            text-decoration: none;
            transition: background 0.3s;
        }
        
        .cart-section__qty-btn:hover {
            background: linear-gradient(90deg, #3B65C4, #1E3A8A);
        }
        
        .cart-section__qty {
            font-weight: 600;
            min-width: 20px;
            text-align: center;
        }
        
        .cart-section__subtotal {
            font-size: 14px;
            color: #555;
        }
        
        .cart-section__remove-btn {
            position: absolute;
            top: 10px;
            right: 10px;
            color: #FF6347;
            font-size: 20px;
            font-weight: bold;
            text-decoration: none;
        }
        
        .cart-section__summary {
            background: #ffffff;
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            text-align: center;
        }
        
        .cart-section__summary h3 {
            margin: 0 0 10px;
        }
        
        .cart-section__summary-list {
            display: flex;
            flex-direction: column;
            gap: 10px;
            margin-bottom: 15px;
            text-align: left;
        }
        
        .cart-section__summary-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid #f0f0f0;
        }
        
        .cart-section__summary-product {
            display: flex;
            align-items: center;
            gap: 10px;
            flex: 1;
        }
        
        .cart-section__summary-product img {
            width: 40px;
            height: 40px;
            object-fit: cover;
            border-radius: 5px;
        }
        
        .cart-section__summary-price {
            font-weight: 600;
            min-width: 80px;
            text-align: right;
        }
        
        .cart-section__summary-total {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 18px;
            font-weight: 700;
            color: #1E3A8A;
            margin-top: 15px;
            padding-top: 15px;
            border-top: 2px solid #1E3A8A;
        }
        
        .cart-section__validate-btn {
            display: inline-block;
            padding: 12px 20px;
            background: linear-gradient(90deg, #1E3A8A, #3B65C4);
            color: white;
            border-radius: 8px;
            text-decoration: none;
            margin-top: 15px;
            transition: background 0.3s;
        }
        
        .cart-section__validate-btn:hover {
            background: linear-gradient(90deg, #3B65C4, #1E3A8A);
        }
        
        .cart-section__empty-cart {
            text-align: center;
            font-size: 18px;
            color: #555;
            padding: 40px 20px;
        }
        
        @media (max-width: 768px) {
            .cart-section__container {
                grid-template-columns: 1fr;
            }
            .cart-section__item {
                flex-direction: column;
                align-items: flex-start;
            }
            .cart-section__item img {
                width: 100%;
                height: auto;
            }
            .cart-section__quantity-controls {
                justify-content: flex-start;
            }
        }
    </style>
    ''',

    'about.html': '''
    <style>
        .section {
            padding: 60px 20px;
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .section h2 {
            font-size: 36px;
            font-weight: 700;
            text-align: center;
            margin-bottom: 40px;
            color: #1E3A8A;
        }
        
        .seo-intro {
            text-align: center;
            padding: 40px 20px;
        }
        
        .seo-intro h1 {
            font-size: 32px;
            color: #1E3A8A;
            margin-bottom: 20px;
        }
        
        .seo-intro p {
            font-size: 16px;
            color: #555;
            line-height: 1.6;
        }
        
        .center-container {
            max-width: 900px;
            margin: 0 auto;
        }
        
        .content-box {
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        
        .about-container {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 30px;
            justify-content: center;
        }
        
        .about-container img {
            width: 300px;
            max-width: 100%;
            height: auto;
            border-radius: 15px;
            object-fit: cover;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        
        .about-text {
            flex: 1;
            min-width: 300px;
        }
        
        .about-text p {
            font-size: 16px;
            line-height: 1.6;
            color: #333;
            margin-bottom: 15px;
        }
        
        .about-buttons {
            display: flex;
            gap: 15px;
            margin-top: 20px;
        }
        
        .btn-primary {
            display: inline-block;
            padding: 12px 25px;
            background: linear-gradient(90deg, #1E3A8A, #3B65C4);
            color: white;
            border-radius: 8px;
            text-decoration: none;
            text-align: center;
            transition: background 0.3s;
        }
        
        .btn-primary:hover {
            background: linear-gradient(90deg, #3B65C4, #1E3A8A);
        }
        
        .gallery-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 30px;
        }
        
        .artwork-card {
            position: relative;
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        
        .artwork-image-wrapper {
            position: relative;
            width: 100%;
            height: 200px;
            overflow: hidden;
        }
        
        .artwork-image-wrapper img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        
        .artwork-name {
            padding: 10px;
            text-align: center;
            font-weight: 600;
            color: #1E3A8A;
        }
        
        .favorite-btn {
            position: absolute;
            top: 10px;
            right: 10px;
            font-size: 24px;
            cursor: pointer;
            background: rgba(255,255,255,0.8);
            border-radius: 50%;
            width: 40px;
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            text-decoration: none;
            transition: background 0.3s;
        }
        
        .favorite-btn:hover {
            background: rgba(255,255,255,1);
        }
        
        .contact-cta {
            background: linear-gradient(90deg, #1E3A8A, #3B65C4);
            color: white;
            border-radius: 15px;
            padding: 60px 20px;
            text-align: center;
        }
        
        .contact-cta h2 {
            color: white;
        }
        
        .contact-cta p {
            font-size: 16px;
            margin-bottom: 20px;
        }
        
        .btn-contact {
            background: white;
            color: #1E3A8A;
        }
        
        .btn-contact:hover {
            background: #f0f0f0;
        }
        
        @media (max-width: 768px) {
            .about-container {
                flex-direction: column;
            }
            .about-buttons {
                flex-direction: column;
            }
            .gallery-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
    ''',

    'boutique.html': '''
    <style>
        .section {
            padding: 60px 20px;
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .section h2 {
            font-size: 36px;
            font-weight: 700;
            text-align: center;
            margin-bottom: 40px;
            color: #1E3A8A;
        }
        
        .seo-intro {
            text-align: center;
            padding: 40px 20px;
        }
        
        .seo-intro h1 {
            font-size: 32px;
            color: #1E3A8A;
            margin-bottom: 20px;
        }
        
        .seo-intro p {
            font-size: 16px;
            color: #555;
            line-height: 1.6;
        }
        
        .latest-gallery {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 25px;
            margin-top: 20px;
        }
        
        .latest-artwork {
            position: relative;
            background: #ffffff;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
            transition: transform 0.3s, box-shadow 0.3s;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        
        .latest-artwork:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 25px rgba(0,0,0,0.15);
        }
        
        .latest-artwork .badge {
            position: absolute;
            top: 10px;
            left: 10px;
            background: linear-gradient(90deg, #FF7F50, #FF4500);
            color: white;
            font-size: 12px;
            font-weight: 700;
            padding: 5px 10px;
            border-radius: 20px;
            text-transform: uppercase;
            z-index: 10;
        }
        
        .artwork-image-wrapper {
            position: relative;
            width: 100%;
            height: 280px;
            overflow: hidden;
        }
        
        .artwork-image-wrapper img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        
        .favorite-btn {
            position: absolute;
            top: 10px;
            right: 10px;
            font-size: 24px;
            cursor: pointer;
            background: rgba(255,255,255,0.8);
            border-radius: 50%;
            width: 40px;
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            text-decoration: none;
            transition: background 0.3s;
        }
        
        .favorite-btn:hover {
            background: rgba(255,255,255,1);
        }
        
        .info {
            padding: 15px;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        
        .info h3 {
            margin: 0;
            font-size: 18px;
            font-weight: 700;
            color: #1E3A8A;
        }
        
        .info p {
            margin: 0;
            font-weight: 600;
            color: #333;
        }
        
        .buy-btn {
            margin-top: 10px;
            padding: 10px 15px;
            background: linear-gradient(90deg, #1E3A8A, #3B65C4);
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            transition: background 0.3s;
        }
        
        .buy-btn:hover {
            background: linear-gradient(90deg, #3B65C4, #1E3A8A);
        }
        
        @media (max-width: 768px) {
            .latest-gallery {
                grid-template-columns: 1fr;
            }
        }
    </style>
    ''',

    'galerie.html': '''
    <style>
        .section {
            padding: 60px 20px;
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .section h2 {
            font-size: 36px;
            font-weight: 700;
            text-align: center;
            margin-bottom: 40px;
            color: #1E3A8A;
        }
        
        .seo-intro {
            text-align: center;
            padding: 40px 20px;
        }
        
        .seo-intro h1 {
            font-size: 32px;
            color: #1E3A8A;
            margin-bottom: 20px;
        }
        
        .seo-intro p {
            font-size: 16px;
            color: #555;
            line-height: 1.6;
        }
        
        .gallery-masonry {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 30px;
        }
        
        .gallery-item {
            position: relative;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        
        .gallery-image-wrapper {
            position: relative;
            width: 100%;
            height: 300px;
            overflow: hidden;
        }
        
        .gallery-image-wrapper img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            transition: transform 0.3s;
        }
        
        .gallery-item:hover .gallery-image-wrapper img {
            transform: scale(1.05);
        }
        
        .favorite-btn {
            position: absolute;
            top: 10px;
            right: 10px;
            font-size: 24px;
            cursor: pointer;
            background: rgba(255,255,255,0.8);
            border-radius: 50%;
            width: 40px;
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            text-decoration: none;
            transition: background 0.3s;
        }
        
        .favorite-btn:hover {
            background: rgba(255,255,255,1);
        }
    </style>
    ''',

    'contact.html': '''
    <style>
        .section {
            padding: 60px 20px;
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .auth-section {
            display: flex;
            justify-content: center;
            padding: 60px 20px;
        }
        
        .auth-container {
            background: white;
            border-radius: 15px;
            padding: 40px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
            max-width: 500px;
            width: 100%;
        }
        
        .auth-container h2 {
            color: #1E3A8A;
            text-align: center;
            margin-bottom: 30px;
            font-size: 28px;
        }
        
        .auth-form {
            display: flex;
            flex-direction: column;
            gap: 15px;
        }
        
        .auth-form label {
            font-weight: 600;
            color: #333;
        }
        
        .auth-form input,
        .auth-form textarea {
            padding: 12px;
            border: 1px solid #ccc;
            border-radius: 8px;
            font-size: 14px;
            font-family: Poppins, sans-serif;
        }
        
        .auth-form textarea {
            resize: vertical;
            min-height: 150px;
        }
        
        .auth-form button {
            padding: 12px;
            background: linear-gradient(90deg, #1E3A8A, #3B65C4);
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
            transition: background 0.3s;
        }
        
        .auth-form button:hover {
            background: linear-gradient(90deg, #3B65C4, #1E3A8A);
        }
        
        .flash-messages {
            list-style: none;
            padding: 0;
            margin-bottom: 20px;
        }
        
        .flash-messages li {
            background: #f44336;
            color: white;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 10px;
        }
    </style>
    ''',

    'profile.html': '''
    <style>
        .profile-header {
            background: linear-gradient(90deg, #1E3A8A, #3B65C4);
            color: white;
            padding: 60px 20px;
            text-align: center;
        }
        
        .profile-header h1 {
            font-size: 36px;
            margin-bottom: 10px;
        }
        
        .profile-email {
            font-size: 18px;
            opacity: 0.9;
        }
        
        .profile-meta {
            font-size: 14px;
            opacity: 0.8;
        }
        
        .section {
            padding: 60px 20px;
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .profile-details {
            background: #f9f9f9;
        }
        
        .profile-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 30px;
            margin-bottom: 40px;
        }
        
        .profile-card {
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        
        .profile-card h3 {
            color: #1E3A8A;
            margin-bottom: 20px;
            font-size: 20px;
        }
        
        .info-group {
            display: flex;
            flex-direction: column;
            gap: 15px;
        }
        
        .info-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid #f0f0f0;
        }
        
        .info-label {
            font-weight: 600;
            color: #333;
        }
        
        .info-value {
            color: #666;
        }
        
        .quick-actions {
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        
        .action-btn {
            display: block;
            padding: 12px;
            background: linear-gradient(90deg, #1E3A8A, #3B65C4);
            color: white;
            border-radius: 8px;
            text-decoration: none;
            text-align: center;
            transition: background 0.3s;
        }
        
        .action-btn:hover {
            background: linear-gradient(90deg, #3B65C4, #1E3A8A);
        }
        
        .section-header {
            text-align: center;
            margin-bottom: 30px;
        }
        
        .section-header h2 {
            font-size: 28px;
            color: #1E3A8A;
            margin: 0;
        }
        
        .favorites-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }
        
        .favorite-card {
            position: relative;
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        
        .favorite-image {
            position: relative;
            width: 100%;
            height: 200px;
            overflow: hidden;
        }
        
        .favorite-image img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        
        .favorite-btn {
            position: absolute;
            top: 10px;
            right: 10px;
            font-size: 24px;
            cursor: pointer;
            background: rgba(255,255,255,0.8);
            border-radius: 50%;
            width: 40px;
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            text-decoration: none;
            transition: background 0.3s;
        }
        
        .favorite-btn:hover {
            background: rgba(255,255,255,1);
        }
        
        .favorite-title {
            padding: 10px;
            text-align: center;
            font-weight: 600;
            color: #1E3A8A;
        }
        
        .orders-table-wrapper {
            overflow-x: auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        
        .orders-table {
            width: 100%;
            border-collapse: collapse;
        }
        
        .orders-table thead {
            background: #1E3A8A;
            color: white;
        }
        
        .orders-table th {
            padding: 15px;
            text-align: left;
            font-weight: 600;
        }
        
        .orders-table td {
            padding: 15px;
            border-bottom: 1px solid #f0f0f0;
        }
        
        .status-badge {
            display: inline-block;
            padding: 5px 10px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }
        
        .status-en-cours {
            background: #FFF3CD;
            color: #856404;
        }
        
        .status-confirmée {
            background: #CCE5FF;
            color: #004085;
        }
        
        .status-expédiée {
            background: #D1ECF1;
            color: #0C5460;
        }
        
        .status-livrée {
            background: #D4EDDA;
            color: #155724;
        }
        
        .empty-state {
            text-align: center;
            padding: 40px 20px;
            color: #666;
        }
        
        @media (max-width: 768px) {
            .profile-grid {
                grid-template-columns: 1fr;
            }
            .favorites-grid {
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            }
        }
    </style>
    ''',

    'footer.html': '''
    <style>
        .site-footer {
            background-color: #1E3A8A;
            color: white;
            padding: 40px 20px 20px 20px;
            font-family: 'Arial', sans-serif;
        }
        
        .footer-container {
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            gap: 30px;
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .footer-about, .footer-links, .footer-contact {
            flex: 1 1 200px;
            min-width: 200px;
        }
        
        .footer-about h3, .footer-links h4, .footer-contact h4 {
            margin-bottom: 10px;
            font-size: 18px;
        }
        
        .footer-links ul {
            list-style: none;
            padding: 0;
        }
        
        .footer-links ul li {
            margin-bottom: 8px;
        }
        
        .footer-links ul li a {
            color: white;
            text-decoration: none;
            transition: color 0.3s;
        }
        
        .footer-links ul li a:hover {
            color: #FFC107;
        }
        
        .footer-contact p {
            margin: 5px 0;
        }
        
        .footer-contact a {
            color: white;
            text-decoration: none;
        }
        
        .footer-contact a:hover {
            color: #FFC107;
        }
        
        .footer-bottom {
            text-align: center;
            margin-top: 20px;
            font-size: 14px;
            border-top: 1px solid rgba(255,255,255,0.3);
            padding-top: 10px;
        }
        
        @media (max-width: 768px) {
            .footer-container {
                flex-direction: column;
                text-align: center;
            }
            .footer-about, .footer-links, .footer-contact {
                flex: 1 1 100%;
            }
        }
    </style>
    ''',

    'checkout_success.html': '''
    <style>
        .success-container {
            max-width: 600px;
            margin: 60px auto;
            background: white;
            border-radius: 15px;
            padding: 40px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
            text-align: center;
        }
        
        .success-icon {
            font-size: 64px;
            margin-bottom: 20px;
        }
        
        .success-container h2 {
            color: #4CAF50;
            margin-bottom: 10px;
        }
        
        .success-container p {
            color: #666;
            line-height: 1.6;
            margin-bottom: 20px;
        }
        
        .order-details {
            background: #f9f9f9;
            border-radius: 10px;
            padding: 20px;
            margin: 20px 0;
            text-align: left;
        }
        
        .detail-row {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #f0f0f0;
        }
        
        .detail-row:last-child {
            border-bottom: none;
        }
        
        .detail-label {
            font-weight: 600;
            color: #333;
        }
        
        .detail-value {
            color: #1E3A8A;
            font-weight: 700;
        }
    </style>
    ''',

    'order.html': '''
    <style>
        .orders-section {
            padding: 60px 20px;
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .orders-section h2 {
            font-size: 28px;
            color: #1E3A8A;
            text-align: center;
            margin-bottom: 40px;
        }
        
        .orders-list {
            display: grid;
            grid-template-columns: 1fr;
            gap: 20px;
        }
        
        .order-card {
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        
        .order-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #f0f0f0;
        }
        
        .order-header h3 {
            color: #1E3A8A;
            margin: 0;
        }
        
        .header-right {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        .order-status {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }
        
        .order-status.en-cours {
            background: #FFF3CD;
            color: #856404;
        }
        
        .order-status.confirmée {
            background: #CCE5FF;
            color: #004085;
        }
        
        .order-status.expédiée {
            background: #D1ECF1;
            color: #0C5460;
        }
        
        .order-status.livrée {
            background: #D4EDDA;
            color: #155724;
        }
        
        .btn-primary {
            display: inline-block;
            padding: 10px 20px;
            background: linear-gradient(90deg, #1E3A8A, #3B65C4);
            color: white;
            border-radius: 8px;
            text-decoration: none;
            transition: background 0.3s;
            font-size: 14px;
        }
        
        .btn-primary:hover {
            background: linear-gradient(90deg, #3B65C4, #1E3A8A);
        }
        
        .order-info-card {
            background: #f9f9f9;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 20px;
        }
        
        .info-item {
            padding: 8px 0;
            display: flex;
            justify-content: space-between;
        }
        
        .info-item strong {
            color: #333;
        }
        
        .total-price {
            color: #1E3A8A;
            font-weight: 700;
        }
        
        .order-items {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        
        .order-item {
            display: flex;
            gap: 10px;
            background: #f9f9f9;
            padding: 10px;
            border-radius: 8px;
        }
        
        .order-item img {
            width: 60px;
            height: 60px;
            object-fit: cover;
            border-radius: 5px;
        }
        
        .order-item-info {
            flex: 1;
        }
        
        .order-item-info .name {
            font-weight: 600;
            color: #1E3A8A;
            margin: 0;
        }
        
        .order-item-info .details {
            font-size: 12px;
            color: #666;
            margin: 0;
        }
    </style>
    ''',

    'order_status.html': '''
    <style>
        .order-status {
            padding: 60px 20px;
            max-width: 900px;
            margin: 0 auto;
        }
        
        .order-status h2 {
            color: #1E3A8A;
            text-align: center;
            margin-bottom: 30px;
        }
        
        .btn-primary {
            display: inline-block;
            padding: 10px 20px;
            background: linear-gradient(90deg, #1E3A8A, #3B65C4);
            color: white;
            border-radius: 8px;
            text-decoration: none;
            transition: background 0.3s;
            float: right;
            margin-bottom: 20px;
        }
        
        .btn-primary:hover {
            background: linear-gradient(90deg, #3B65C4, #1E3A8A);
        }
        
        .order-info-card {
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            margin-bottom: 30px;
            clear: both;
        }
        
        .info-item {
            padding: 12px 0;
            border-bottom: 1px solid #f0f0f0;
            display: flex;
            justify-content: space-between;
        }
        
        .info-item strong {
            color: #333;
        }
        
        .status {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 12px;
        }
        
        .status.en-cours {
            background: #FFF3CD;
            color: #856404;
        }
        
        .status.confirmée {
            background: #CCE5FF;
            color: #004085;
        }
        
        .status.expédiée {
            background: #D1ECF1;
            color: #0C5460;
        }
        
        .status.livrée {
            background: #D4EDDA;
            color: #155724;
        }
        
        .order-items {
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }
        
        .order-items h3 {
            color: #1E3A8A;
            margin-top: 0;
        }
        
        .order-items table {
            width: 100%;
            border-collapse: collapse;
        }
        
        .order-items thead {
            background: #f9f9f9;
        }
        
        .order-items th {
            padding: 12px;
            text-align: left;
            font-weight: 600;
            border-bottom: 2px solid #1E3A8A;
        }
        
        .order-items td {
            padding: 12px;
            border-bottom: 1px solid #f0f0f0;
        }
        
        .order-items img {
            width: 50px;
            height: 50px;
            object-fit: cover;
            border-radius: 5px;
        }
        
        .order-total {
            text-align: right;
            font-size: 18px;
            font-weight: 700;
            color: #1E3A8A;
        }
    </style>
    '''
}

def main():
    import os
    from pathlib import Path
    
    templates_dir = Path('c:\\Users\\cococ\\Desktop\\Projet_JB\\templates')
    
    for template_name, style_block in TEMPLATE_STYLES.items():
        template_path = templates_dir / template_name
        
        if template_path.exists():
            content = template_path.read_text(encoding='utf-8')
            
            # Vérifier si le bloc style existe déjà
            if '<style>' in content:
                print(f"⏭️  {template_name} - Style déjà présent, skip")
                continue
            
            # Ajouter le bloc style avant </head> ou {% endblock %}
            if '{% endblock %}' in content:
                content = content.replace('{% endblock %}', f'{style_block}\n{{% endblock %}}', 1)
            elif '</html>' in content:
                content = content.replace('</html>', f'{style_block}\n</html>', 1)
            else:
                content += style_block
            
            template_path.write_text(content, encoding='utf-8')
            print(f"✅ {template_name} - Styles ajoutés")
        else:
            print(f"❌ {template_name} - Fichier non trouvé")

if __name__ == '__main__':
    main()
