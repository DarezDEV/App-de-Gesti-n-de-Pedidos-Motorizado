# recommendation_ai_service.py Error al cargar modelos
from flask import jsonify, request
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MinMaxScaler
import joblib
from app.db import get_db_connection
import os
from datetime import datetime

class RecommendationAIService:
    """Servicio de IA para generar recomendaciones de productos personalizadas basadas en el comportamiento del usuario"""
    
    # Rutas para guardar y cargar los modelos
    MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models')
    SIMILARITY_MATRIX_PATH = os.path.join(MODEL_DIR, 'similarity_matrix.pkl')
    USER_VECTORS_PATH = os.path.join(MODEL_DIR, 'user_vectors.pkl')
    
    def __init__(self):
        if not os.path.exists(self.MODEL_DIR):
            os.makedirs(self.MODEL_DIR)
        self.similarity_matrix = None
        self.user_vectors = {}
        self.load_models()
        if self.similarity_matrix is None or not self.user_vectors:
            print("Modelos no encontrados, iniciando entrenamiento...")
            self.build_collaborative_filtering_model(force_rebuild=True)
    
    def load_models(self):
        try:
            if os.path.exists(self.SIMILARITY_MATRIX_PATH):
                self.similarity_matrix = joblib.load(self.SIMILARITY_MATRIX_PATH)
            if os.path.exists(self.USER_VECTORS_PATH):
                self.user_vectors = joblib.load(self.USER_VECTORS_PATH)
            print("Modelos de recomendación cargados correctamente")
        except Exception as e:
            print(f"Error al cargar modelos: {str(e)}")
            self.similarity_matrix = None
            self.user_vectors = {}
    
    def save_models(self):
        try:
            joblib.dump(self.similarity_matrix, self.SIMILARITY_MATRIX_PATH)
            joblib.dump(self.user_vectors, self.USER_VECTORS_PATH)
            print("Modelos de recomendación guardados correctamente")
        except Exception as e:
            print(f"Error al guardar modelos: {str(e)}")
    
    @staticmethod
    def get_product_data():
        """Obtiene todos los productos activos de la base de datos"""
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT p.id, p.name, p.description, p.price, p.category_id,
                   c.name as category_name
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            WHERE p.estado = 1
        """)
        
        products = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return products
    
    @staticmethod
    def get_user_interactions(days=30, min_interactions=100):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT user_id, product_id, 'view' as interaction_type FROM product_views
            WHERE viewed_at > DATE_SUB(NOW(), INTERVAL %s DAY)
        """, (days,))
        views = cursor.fetchall()
        cursor.execute("""
            SELECT user_id, product_id, 'cart' as interaction_type FROM cart
        """)
        cart_items = cursor.fetchall()
        cursor.close()
        conn.close()
        interactions = views + cart_items
        if len(interactions) < min_interactions:
            print(f"Interacciones insuficientes para entrenar ({len(interactions)})")
            return None
        df_interactions = pd.DataFrame(interactions)
        df_interactions['weight'] = df_interactions['interaction_type'].apply(lambda x: 1.0 if x == 'view' else 3.0)
        return df_interactions
    
    def build_collaborative_filtering_model(self, force_rebuild=False):
        if self.similarity_matrix is not None and not force_rebuild:
            return True
        interactions_df = self.get_user_interactions()
        if interactions_df is None:
            return False
        user_product_matrix = interactions_df.pivot_table(index='user_id', columns='product_id', values='weight', aggfunc='sum', fill_value=0)
        scaler = MinMaxScaler()
        for user_id in user_product_matrix.index:
            user_row = user_product_matrix.loc[user_id].values.reshape(1, -1)
            if user_row.sum() > 0:
                user_product_matrix.loc[user_id] = scaler.fit_transform(user_row).flatten()
        product_similarity = cosine_similarity(user_product_matrix.T)
        self.similarity_matrix = pd.DataFrame(product_similarity, index=user_product_matrix.columns, columns=user_product_matrix.columns)
        for user_id in user_product_matrix.index:
            self.user_vectors[user_id] = user_product_matrix.loc[user_id].to_dict()
        self.save_models()
        return True
    
    def compute_content_based_similarity(self, product_id, product_data):
        """
        Calcula la similitud basada en contenido entre un producto y los demás
        
        Args:
            product_id: ID del producto base
            product_data: Datos de todos los productos
            
        Returns:
            dict: Diccionario con IDs de productos y puntuaciones de similitud
        """
        # Filtrar para encontrar el producto base
        base_product = None
        for product in product_data:
            if product['id'] == product_id:
                base_product = product
                break
        
        if base_product is None:
            return {}
        
        similarity_scores = {}
        
        for product in product_data:
            if product['id'] == product_id:
                continue  # Omitir el mismo producto
            
            score = 0.0
            
            # Similitud por categoría (factor importante)
            if product['category_id'] == base_product['category_id']:
                score += 0.5
            
            # Similitud por rango de precio
            base_price = float(base_product['price'])
            current_price = float(product['price'])
            price_diff = abs(base_price - current_price) / max(base_price, 1)
            if price_diff < 0.1:  # Diferencia menor al 10%
                score += 0.3
            elif price_diff < 0.3:  # Diferencia menor al 30%
                score += 0.1
            
            # Ajustar el puntaje final
            similarity_scores[product['id']] = min(score, 1.0)
        
        return similarity_scores
    
    def get_recommendations_for_user(self, user_id, limit=4):
        """
        Obtiene recomendaciones de productos para un usuario usando un enfoque híbrido
        
        Args:
            user_id (int): ID del usuario
            limit (int): Número máximo de recomendaciones a devolver
        
        Returns:
            list: Lista de productos recomendados
        """
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener productos del carrito
        cursor.execute("""
            SELECT product_id FROM cart WHERE user_id = %s
        """, (user_id,))
        cart_product_ids = [item['product_id'] for item in cursor.fetchall()]
        
        # Obtener productos vistos recientemente (últimos 7 días)
        cursor.execute("""
            SELECT product_id FROM product_views
            WHERE user_id = %s AND viewed_at > DATE_SUB(NOW(), INTERVAL 7 DAY)
            ORDER BY viewed_at DESC LIMIT 10
        """, (user_id,))
        viewed_product_ids = [item['product_id'] for item in cursor.fetchall()]
        
        # Unir productos del carrito y vistos
        product_ids_to_analyze = list(set(cart_product_ids + viewed_product_ids))
        
        # Obtener todos los productos activos
        cursor.execute("""
            SELECT id, name, description, price, category_id, image, image2, image3, stock
            FROM products WHERE estado = 1
        """)
        all_products = cursor.fetchall()
        all_product_ids = [p['id'] for p in all_products]
        
        # Si no hay datos de usuario o modelo, usar recomendaciones básicas
        if not product_ids_to_analyze or self.similarity_matrix is None:
            print("Usando recomendaciones básicas (sin datos de usuario o modelo)")
            # Importante: excluir productos del carrito en las recomendaciones básicas
            if cart_product_ids:
                placeholders = ','.join(['%s'] * len(cart_product_ids))
                cursor.execute(f"""
                    SELECT * FROM products 
                    WHERE estado = 1 AND id NOT IN ({placeholders})
                    ORDER BY RAND() LIMIT %s
                """, cart_product_ids + [limit])
            else:
                cursor.execute("""
                    SELECT * FROM products WHERE estado = 1 ORDER BY RAND() LIMIT %s
                """, (limit,))
            recommendations = cursor.fetchall()
            cursor.close()
            conn.close()
            return recommendations
        
        # Intentar construir modelo si no existe
        if self.similarity_matrix is None:
            self.build_collaborative_filtering_model()
        
        # Productos a excluir (los que ya están en el carrito)
        exclude_ids = set(cart_product_ids)
        
        # Calcular puntuaciones para cada producto
        product_scores = {}
        
        # 1. Métodos basados en productos similares a los del carrito y vistos (filtrado colaborativo)
        for product_id in product_ids_to_analyze:
            # Verificar si el producto está en la matriz de similitud
            if product_id in self.similarity_matrix.index:
                # Obtener productos similares con sus puntuaciones
                similar_products = self.similarity_matrix[product_id].sort_values(ascending=False)
                
                # Asignar puntuaciones
                for similar_id, score in similar_products.items():
                    if similar_id in exclude_ids:
                        continue  # Saltar productos que ya están en el carrito
                    if similar_id in product_scores:
                        product_scores[similar_id] = max(product_scores[similar_id], score)
                    else:
                        product_scores[similar_id] = score
        
        # 2. Considerar perfil del usuario si existe (recomendación basada en usuario)
        if user_id in self.user_vectors:
            user_vector = self.user_vectors[user_id]
            for product_id in all_product_ids:
                if product_id in exclude_ids:
                    continue  # Saltar productos que ya están en el carrito
                if product_id in user_vector and user_vector[product_id] > 0:
                    if product_id in product_scores:
                        product_scores[product_id] += user_vector[product_id] * 0.2  # Peso adicional
                    else:
                        product_scores[product_id] = user_vector[product_id] * 0.2
        
        # 3. Añadir recomendaciones basadas en contenido
        product_data = self.get_product_data()
        for product_id in product_ids_to_analyze:
            content_scores = self.compute_content_based_similarity(product_id, product_data)
            for p_id, score in content_scores.items():
                if p_id in exclude_ids:
                    continue  # Saltar productos que ya están en el carrito
                if p_id in product_scores:
                    product_scores[p_id] = max(product_scores[p_id], score * 0.8)  # Peso menor que similitud colaborativa
                else:
                    product_scores[p_id] = score * 0.8
        
        # Eliminar productos que ya están en el carrito (verificación extra)
        for exclude_id in exclude_ids:
            if exclude_id in product_scores:
                del product_scores[exclude_id]
        
        # Ordenar productos por puntuación y tomar los mejores
        sorted_products = sorted(product_scores.items(), key=lambda x: x[1], reverse=True)
        top_product_ids = [p_id for p_id, _ in sorted_products[:limit]]
        
        # Si no hay suficientes recomendaciones, completar con productos aleatorios
        if len(top_product_ids) < limit:
            remaining = limit - len(top_product_ids)
            existing_ids = set(top_product_ids + list(exclude_ids))
            available_ids = [p_id for p_id in all_product_ids if p_id not in existing_ids]
            
            if available_ids:
                import random
                random_ids = random.sample(available_ids, min(remaining, len(available_ids)))
                top_product_ids.extend(random_ids)
        
        # Obtener información completa de los productos recomendados
        if top_product_ids:
            placeholders = ','.join(['%s'] * len(top_product_ids))
            cursor.execute(f"""
                SELECT * FROM products
                WHERE id IN ({placeholders}) AND estado = 1
            """, top_product_ids)
            recommendations = cursor.fetchall()
            
            # Reordenar según la puntuación original
            recommendations_ordered = []
            for p_id in top_product_ids:
                for product in recommendations:
                    if product['id'] == p_id:
                        recommendations_ordered.append(product)
                        break
            recommendations = recommendations_ordered
        else:
            # Fallback a recomendaciones aleatorias (excluyendo productos del carrito)
            if cart_product_ids:
                placeholders = ','.join(['%s'] * len(cart_product_ids))
                cursor.execute(f"""
                    SELECT * FROM products 
                    WHERE estado = 1 AND id NOT IN ({placeholders})
                    ORDER BY RAND() LIMIT %s
                """, cart_product_ids + [limit])
            else:
                cursor.execute("""
                    SELECT * FROM products WHERE estado = 1 ORDER BY RAND() LIMIT %s
                """, (limit,))
            recommendations = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # Registrar estas recomendaciones para análisis futuro
        self.log_recommendations(user_id, [r['id'] for r in recommendations])
        
        return recommendations
    
    def log_recommendations(self, user_id, product_ids):
        """
        Registra las recomendaciones hechas para análisis posterior
        """
        if not product_ids:
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            for product_id in product_ids:
                cursor.execute("""
                    INSERT INTO recommendation_logs (user_id, product_id, recommended_at)
                    VALUES (%s, %s, NOW())
                """, (user_id, product_id))
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Error al registrar recomendaciones: {str(e)}")
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def track_product_view(user_id, product_id):
        """
        Registra que un usuario ha visto un producto y actualiza relaciones entre productos.
        También registra para el entrenamiento del modelo.
        
        Args:
            user_id (int): ID del usuario
            product_id (int): ID del producto
            
        Returns:
            bool: True si se registró correctamente, False en caso contrario
        """
        if not user_id or not product_id:
            return False
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Registrar vista
            cursor.execute("""
                INSERT INTO product_views (user_id, product_id)
                VALUES (%s, %s)
            """, (user_id, product_id))
            
            # Registrar relaciones con otros productos vistos recientemente
            cursor.execute("""
                SELECT product_id FROM product_views
                WHERE user_id = %s AND product_id != %s
                ORDER BY viewed_at DESC LIMIT 5
            """, (user_id, product_id))
            
            recent_products = cursor.fetchall()
            for recent in recent_products:
                cursor.execute("""
                    INSERT INTO product_relationships
                    (source_product_id, related_product_id, relationship_strength)
                    VALUES (%s, %s, 1)
                    ON DUPLICATE KEY UPDATE relationship_strength = relationship_strength + 1
                """, (recent[0], product_id))
                
                # También relación inversa con menor peso
                cursor.execute("""
                    INSERT INTO product_relationships
                    (source_product_id, related_product_id, relationship_strength)
                    VALUES (%s, %s, 0.5)
                    ON DUPLICATE KEY UPDATE relationship_strength = relationship_strength + 0.5
                """, (product_id, recent[0]))
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Error al registrar vista de producto: {str(e)}")
            return False
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def analyze_cart_patterns(user_id):
        """
        Analiza patrones en el carrito del usuario para entender sus preferencias.
        
        Args:
            user_id (int): ID del usuario
            
        Returns:
            dict: Diccionario con patrones identificados
        """
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT p.id, p.name, p.category_id, c.name as category_name, p.price,
                   cart.quantity
            FROM cart cart
            JOIN products p ON cart.product_id = p.id
            JOIN categories c ON p.category_id = c.id
            WHERE cart.user_id = %s
        """, (user_id,))
        
        cart_items = cursor.fetchall()
        
        # Obtener también historial de vistas recientes
        cursor.execute("""
            SELECT p.id, p.name, p.category_id, c.name as category_name, p.price,
                   COUNT(*) as view_count
            FROM product_views pv
            JOIN products p ON pv.product_id = p.id
            JOIN categories c ON p.category_id = c.id
            WHERE pv.user_id = %s AND pv.viewed_at > DATE_SUB(NOW(), INTERVAL 30 DAY)
            GROUP BY p.id
        """, (user_id,))
        
        viewed_items = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        patterns = {
            'categories': {},
            'price_range': {'min': 0, 'max': 0, 'avg': 0},
            'favorite_categories': [],
            'price_sensitivity': 'medium',  # default
            'browsing_patterns': {
                'views_to_cart_ratio': 0,
                'category_consistency': 0
            }
        }
        
        # Analizar productos en carrito
        if cart_items:
            # Análisis de categorías
            category_counts = {}
            cart_prices = []
            cart_quantity = 0
            
            for item in cart_items:
                category_id = item['category_id']
                if category_id in category_counts:
                    category_counts[category_id]['count'] += item['quantity']
                    category_counts[category_id]['products'].append(item['id'])
                else:
                    category_counts[category_id] = {
                        'name': item['category_name'],
                        'count': item['quantity'],
                        'products': [item['id']]
                    }
                
                # Precios para análisis
                price = float(item['price'])
                for _ in range(item['quantity']):
                    cart_prices.append(price)
                cart_quantity += item['quantity']
            
            # Actualizar categorías en patrones
            patterns['categories'] = category_counts
            
            # Calcular rango de precios
            if cart_prices:
                patterns['price_range']['min'] = min(cart_prices)
                patterns['price_range']['max'] = max(cart_prices)
                patterns['price_range']['avg'] = sum(cart_prices) / len(cart_prices)
                
                # Determinar sensibilidad al precio
                price_range = patterns['price_range']['max'] - patterns['price_range']['min']
                if price_range > patterns['price_range']['avg'] * 0.5:
                    patterns['price_sensitivity'] = 'low'  # Amplio rango de precios
                elif price_range < patterns['price_range']['avg'] * 0.2:
                    patterns['price_sensitivity'] = 'high'  # Rango estrecho
                
            # Categorías favoritas (ordenadas por cantidad)
            sorted_categories = sorted(
                category_counts.items(), 
                key=lambda x: x[1]['count'], 
                reverse=True
            )
            patterns['favorite_categories'] = [
                {'id': cat_id, 'name': info['name'], 'count': info['count']}
                for cat_id, info in sorted_categories
            ]
        
        # Analizar patrones de navegación combinando carrito y vistas
        if viewed_items:
            view_categories = {}
            for item in viewed_items:
                cat_id = item['category_id']
                if cat_id in view_categories:
                    view_categories[cat_id] += item['view_count']
                else:
                    view_categories[cat_id] = item['view_count']
            
            # Calcular consistencia de categorías (qué tan concentrado está en pocas categorías)
            total_views = sum(view_categories.values())
            category_consistency = 0
            
            if total_views > 0:
                # Si todas las vistas están en una categoría, la consistencia es 1
                # Si están distribuidas uniformemente, será cercana a 0
                normalized_counts = [count/total_views for count in view_categories.values()]
                category_consistency = sum(nc**2 for nc in normalized_counts)  # Similar al índice Herfindahl
            
            patterns['browsing_patterns']['category_consistency'] = category_consistency
            
            # Calcular razón de conversión (vistas a carrito)
            if cart_quantity > 0 and total_views > 0:
                patterns['browsing_patterns']['views_to_cart_ratio'] = cart_quantity / total_views
        
        return patterns
    
    def retrain_model(self, days=30):
        """
        Reentrenar el modelo con datos actualizados.
        Ideal para ejecutar como tarea programada.
        
        Args:
            days (int): Días de datos a considerar para el entrenamiento
            
        Returns:
            bool: True si se reentrenó correctamente, False en caso contrario
        """
        print(f"Iniciando reentrenamiento del modelo de recomendación ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
        
        try:
            success = self.build_collaborative_filtering_model(force_rebuild=True)
            if success:
                print("Modelo reentrenado exitosamente")
            else:
                print("No se pudo reentrenar el modelo")
            return success
        except Exception as e:
            print(f"Error durante el reentrenamiento: {str(e)}")
            return False
    
    @staticmethod
    def evaluate_recommendation_success():
        """
        Evalúa la efectividad de las recomendaciones analizando cuántas
        resultaron en vistas o compras.
        
        Returns:
            dict: Estadísticas de efectividad de recomendaciones
        """
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Consulta para obtener recomendaciones que resultaron en vistas
        cursor.execute("""
            SELECT COUNT(*) as viewed_count 
            FROM recommendation_logs rl
            JOIN product_views pv ON rl.user_id = pv.user_id AND rl.product_id = pv.product_id
            WHERE pv.viewed_at > rl.recommended_at
            AND pv.viewed_at < DATE_ADD(rl.recommended_at, INTERVAL 7 DAY)
        """)
        
        viewed_result = cursor.fetchone()
        viewed_count = viewed_result['viewed_count'] if viewed_result else 0
        
        # Consulta para obtener recomendaciones que resultaron en adiciones al carrito
        cursor.execute("""
            SELECT COUNT(*) as cart_count 
            FROM recommendation_logs rl
            JOIN cart c ON rl.user_id = c.user_id AND rl.product_id = c.product_id
            WHERE c.created_at > rl.recommended_at
            AND c.created_at < DATE_ADD(rl.recommended_at, INTERVAL 7 DAY)
        """)
        
        cart_result = cursor.fetchone()
        cart_count = cart_result['cart_count'] if cart_result else 0
        
        # Número total de recomendaciones
        cursor.execute("SELECT COUNT(*) as total FROM recommendation_logs")
        total_result = cursor.fetchone()
        total_count = total_result['total'] if total_result else 1  # Evitar división por cero
        
        cursor.close()
        conn.close()
        
        # Calcular tasas de conversión
        view_rate = (viewed_count / total_count) * 100 if total_count > 0 else 0
        cart_rate = (cart_count / total_count) * 100 if total_count > 0 else 0
        
        return {
            'total_recommendations': total_count,
            'viewed_recommendations': viewed_count,
            'cart_recommendations': cart_count,
            'view_conversion_rate': round(view_rate, 2),
            'cart_conversion_rate': round(cart_rate, 2),
            'evaluation_date': datetime.now().strftime('%Y-%m-%d')
        }


class Url_recommendation:
    """Controlador de rutas para el servicio de recomendación con IA"""
    
    # Crear una instancia única del servicio
    _recommendation_service = None
    
    @classmethod
    def get_service(cls):
        if cls._recommendation_service is None:
            cls._recommendation_service = RecommendationAIService()
        return cls._recommendation_service
    
    @classmethod
    def get_recommendations(cls, user_id):
        limit = request.args.get('limit', default=4, type=int)
        service = cls.get_service()
        recommendations = service.get_recommendations_for_user(user_id, limit)
        return jsonify(recommendations)

    @classmethod
    def track_product_view(cls):
        """Registra la vista de un producto por parte de un usuario."""
        data = request.json
        user_id = data.get('user_id')
        product_id = data.get('product_id')

        if not user_id or not product_id:
            return jsonify({'error': 'user_id y product_id son requeridos'}), 400

        service = cls.get_service()
        success = service.track_product_view(user_id, product_id)
        return jsonify({'success': success})

    @classmethod
    def analyze_cart_patterns(cls, user_id):
        """Analiza patrones en el carrito del usuario."""
        service = cls.get_service()
        patterns = service.analyze_cart_patterns(user_id)
        return jsonify(patterns)
    
    @classmethod
    def retrain_model(cls):
        if request.method == 'POST':
            service = cls.get_service()
            days = request.args.get('days', default=30, type=int)
            success = service.build_collaborative_filtering_model(force_rebuild=True)
            return jsonify({'success': success})
        return jsonify({'error': 'Método no permitido'}), 405
    
    @classmethod
    def get_model_stats(cls):
        """Obtiene estadísticas del modelo de recomendación."""
        service = cls.get_service()
        stats = service.evaluate_recommendation_success()
        return jsonify(stats)