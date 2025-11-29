# 🌐 Exemples d'Intégration Multi-Langages

## 📱 React / Next.js

### Hook personnalisé pour l'API
```javascript
// hooks/useJBApi.js
import { useState, useEffect } from 'react';

const API_KEY = process.env.NEXT_PUBLIC_JB_API_KEY;
const BASE_URL = process.env.NEXT_PUBLIC_JB_API_URL || 'http://127.0.0.1:5000';

export function useJBApi(endpoint) {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        async function fetchData() {
            try {
                const response = await fetch(`${BASE_URL}/api/export/${endpoint}`, {
                    headers: {
                        'X-API-Key': API_KEY
                    }
                });
                
                const result = await response.json();
                setData(result.data || result.stats);
                setLoading(false);
            } catch (err) {
                setError(err);
                setLoading(false);
            }
        }
        
        fetchData();
    }, [endpoint]);

    return { data, loading, error };
}

// Utilisation dans un composant
function PaintingsGallery() {
    const { data: paintings, loading, error } = useJBApi('paintings');

    if (loading) return <div>Chargement...</div>;
    if (error) return <div>Erreur: {error.message}</div>;

    return (
        <div className="gallery">
            {paintings.map(painting => (
                <div key={painting.id} className="painting-card">
                    <img src={painting.image} alt={painting.name} />
                    <h3>{painting.name}</h3>
                    <p>{painting.price} €</p>
                </div>
            ))}
        </div>
    );
}
```

---

## 🐍 Django

### Service Django
```python
# services/jb_api.py
import requests
from django.conf import settings
from django.core.cache import cache

class JBApiService:
    def __init__(self):
        self.api_key = settings.JB_API_KEY
        self.base_url = settings.JB_API_URL
        self.headers = {'X-API-Key': self.api_key}
    
    def get_paintings(self, use_cache=True):
        """Récupère les peintures avec cache"""
        cache_key = 'jb_paintings'
        
        if use_cache:
            cached = cache.get(cache_key)
            if cached:
                return cached
        
        response = requests.get(
            f"{self.base_url}/api/export/paintings",
            headers=self.headers
        )
        
        if response.status_code == 200:
            data = response.json()['data']
            cache.set(cache_key, data, 3600)  # Cache 1h
            return data
        
        return []
    
    def get_orders(self):
        """Récupère toutes les commandes"""
        response = requests.get(
            f"{self.base_url}/api/export/orders",
            headers=self.headers
        )
        
        if response.status_code == 200:
            return response.json()['data']
        
        return []

# views.py
from django.shortcuts import render
from .services.jb_api import JBApiService

def gallery_view(request):
    api = JBApiService()
    paintings = api.get_paintings()
    
    return render(request, 'gallery.html', {
        'paintings': paintings
    })
```

---

## 🟢 Vue.js / Nuxt

### Service API Vue
```javascript
// services/jbApi.js
export class JBApiService {
    constructor() {
        this.apiKey = process.env.VUE_APP_JB_API_KEY;
        this.baseUrl = process.env.VUE_APP_JB_API_URL || 'http://127.0.0.1:5000';
    }

    async fetchPaintings() {
        const response = await fetch(`${this.baseUrl}/api/export/paintings`, {
            headers: {
                'X-API-Key': this.apiKey
            }
        });
        
        const result = await response.json();
        return result.data;
    }

    async fetchStats() {
        const response = await fetch(`${this.baseUrl}/api/export/stats`, {
            headers: {
                'X-API-Key': this.apiKey
            }
        });
        
        const result = await response.json();
        return result.stats;
    }
}

// store/paintings.js (Vuex)
import { JBApiService } from '@/services/jbApi';

const api = new JBApiService();

export default {
    state: {
        paintings: [],
        loading: false,
        error: null
    },
    
    mutations: {
        SET_PAINTINGS(state, paintings) {
            state.paintings = paintings;
        },
        SET_LOADING(state, loading) {
            state.loading = loading;
        },
        SET_ERROR(state, error) {
            state.error = error;
        }
    },
    
    actions: {
        async fetchPaintings({ commit }) {
            commit('SET_LOADING', true);
            try {
                const paintings = await api.fetchPaintings();
                commit('SET_PAINTINGS', paintings);
            } catch (error) {
                commit('SET_ERROR', error);
            } finally {
                commit('SET_LOADING', false);
            }
        }
    }
};

// components/PaintingsGrid.vue
<template>
    <div class="paintings-grid">
        <div v-if="loading">Chargement...</div>
        <div v-else-if="error">Erreur: {{ error }}</div>
        <div v-else class="grid">
            <div v-for="painting in paintings" :key="painting.id" class="card">
                <img :src="painting.image" :alt="painting.name" />
                <h3>{{ painting.name }}</h3>
                <p>{{ painting.price }} €</p>
            </div>
        </div>
    </div>
</template>

<script>
import { mapState, mapActions } from 'vuex';

export default {
    computed: {
        ...mapState(['paintings', 'loading', 'error'])
    },
    
    methods: {
        ...mapActions(['fetchPaintings'])
    },
    
    mounted() {
        this.fetchPaintings();
    }
};
</script>
```

---

## 🟦 WordPress (PHP)

### Plugin WordPress
```php
<?php
/**
 * Plugin Name: JB Gallery Sync
 * Description: Synchronise les peintures depuis l'API JB
 */

class JB_Gallery_Sync {
    private $api_key;
    private $base_url;
    
    public function __construct() {
        $this->api_key = get_option('jb_api_key', '');
        $this->base_url = get_option('jb_api_url', 'http://127.0.0.1:5000');
        
        add_action('admin_menu', array($this, 'add_admin_menu'));
        add_action('jb_sync_cron', array($this, 'sync_paintings'));
    }
    
    public function add_admin_menu() {
        add_menu_page(
            'JB Gallery',
            'JB Gallery',
            'manage_options',
            'jb-gallery',
            array($this, 'admin_page'),
            'dashicons-art'
        );
    }
    
    public function sync_paintings() {
        $response = wp_remote_get(
            $this->base_url . '/api/export/paintings',
            array(
                'headers' => array(
                    'X-API-Key' => $this->api_key
                )
            )
        );
        
        if (is_wp_error($response)) {
            error_log('JB API Error: ' . $response->get_error_message());
            return;
        }
        
        $body = wp_remote_retrieve_body($response);
        $data = json_decode($body, true);
        
        if (isset($data['data'])) {
            foreach ($data['data'] as $painting) {
                $this->create_or_update_painting($painting);
            }
            
            error_log('JB Sync: ' . count($data['data']) . ' paintings synchronized');
        }
    }
    
    private function create_or_update_painting($painting) {
        // Créer ou mettre à jour un custom post type "painting"
        $post_id = wp_insert_post(array(
            'post_title' => $painting['name'],
            'post_content' => $painting['description'],
            'post_type' => 'painting',
            'post_status' => 'publish'
        ));
        
        if ($post_id) {
            update_post_meta($post_id, 'jb_id', $painting['id']);
            update_post_meta($post_id, 'price', $painting['price']);
            update_post_meta($post_id, 'image', $painting['image']);
            update_post_meta($post_id, 'category', $painting['category']);
        }
    }
    
    public function admin_page() {
        ?>
        <div class="wrap">
            <h1>JB Gallery Sync</h1>
            <button onclick="syncNow()" class="button button-primary">
                Synchroniser maintenant
            </button>
        </div>
        <script>
        function syncNow() {
            fetch('<?php echo admin_url('admin-ajax.php'); ?>?action=jb_sync')
                .then(() => alert('Synchronisation terminée'));
        }
        </script>
        <?php
    }
}

new JB_Gallery_Sync();

// Shortcode pour afficher la galerie
add_shortcode('jb_gallery', function() {
    $args = array(
        'post_type' => 'painting',
        'posts_per_page' => -1
    );
    
    $paintings = get_posts($args);
    
    ob_start();
    ?>
    <div class="jb-gallery">
        <?php foreach ($paintings as $painting): ?>
            <div class="painting-card">
                <img src="<?php echo get_post_meta($painting->ID, 'image', true); ?>" />
                <h3><?php echo $painting->post_title; ?></h3>
                <p><?php echo get_post_meta($painting->ID, 'price', true); ?> €</p>
            </div>
        <?php endforeach; ?>
    </div>
    <?php
    return ob_get_clean();
});
```

---

## 🔵 Angular

### Service Angular
```typescript
// services/jb-api.service.ts
import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { environment } from '../environments/environment';

interface ApiResponse<T> {
  success: boolean;
  data: T;
  count?: number;
}

interface Painting {
  id: number;
  name: string;
  price: number;
  image: string;
  category: string;
  description: string;
}

@Injectable({
  providedIn: 'root'
})
export class JbApiService {
  private apiKey = environment.jbApiKey;
  private baseUrl = environment.jbApiUrl;
  
  private headers = new HttpHeaders({
    'X-API-Key': this.apiKey
  });

  constructor(private http: HttpClient) {}

  getPaintings(): Observable<Painting[]> {
    return this.http.get<ApiResponse<Painting[]>>(
      `${this.baseUrl}/api/export/paintings`,
      { headers: this.headers }
    ).pipe(
      map(response => response.data)
    );
  }

  getStats(): Observable<any> {
    return this.http.get<ApiResponse<any>>(
      `${this.baseUrl}/api/export/stats`,
      { headers: this.headers }
    ).pipe(
      map(response => response.stats)
    );
  }
}

// components/paintings/paintings.component.ts
import { Component, OnInit } from '@angular/core';
import { JbApiService } from '../../services/jb-api.service';

@Component({
  selector: 'app-paintings',
  templateUrl: './paintings.component.html',
  styleUrls: ['./paintings.component.css']
})
export class PaintingsComponent implements OnInit {
  paintings: any[] = [];
  loading = true;
  error: any = null;

  constructor(private jbApi: JbApiService) {}

  ngOnInit(): void {
    this.jbApi.getPaintings().subscribe(
      data => {
        this.paintings = data;
        this.loading = false;
      },
      error => {
        this.error = error;
        this.loading = false;
      }
    );
  }
}
```

---

## 🚀 Automatisation avec GitHub Actions

```yaml
# .github/workflows/sync-jb-data.yml
name: Sync JB Gallery Data

on:
  schedule:
    - cron: '0 */6 * * *'  # Toutes les 6 heures
  workflow_dispatch:  # Manuel

jobs:
  sync:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v2
      
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: pip install requests
      
      - name: Sync data from JB API
        env:
          JB_API_KEY: ${{ secrets.JB_API_KEY }}
          JB_API_URL: ${{ secrets.JB_API_URL }}
        run: |
          python scripts/sync_jb_data.py
      
      - name: Commit changes
        run: |
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          git add data/
          git commit -m "Auto sync: JB Gallery data" || exit 0
          git push
```

---

## 📱 Mobile (React Native)

```javascript
// services/JBApiService.js
import AsyncStorage from '@react-native-async-storage/async-storage';

export class JBApiService {
    constructor() {
        this.apiKey = 'VOTRE_CLE';
        this.baseUrl = 'http://votre-site.com';
    }

    async getPaintings() {
        try {
            // Vérifier le cache
            const cached = await AsyncStorage.getItem('paintings');
            if (cached) {
                const { data, timestamp } = JSON.parse(cached);
                const now = Date.now();
                
                // Si moins de 1h, retourner le cache
                if (now - timestamp < 3600000) {
                    return data;
                }
            }

            // Fetch depuis l'API
            const response = await fetch(
                `${this.baseUrl}/api/export/paintings`,
                {
                    headers: {
                        'X-API-Key': this.apiKey
                    }
                }
            );

            const result = await response.json();
            
            // Mettre en cache
            await AsyncStorage.setItem('paintings', JSON.stringify({
                data: result.data,
                timestamp: Date.now()
            }));

            return result.data;
        } catch (error) {
            console.error('API Error:', error);
            return [];
        }
    }
}

// screens/GalleryScreen.js
import React, { useState, useEffect } from 'react';
import { View, FlatList, Image, Text, StyleSheet } from 'react-native';
import { JBApiService } from '../services/JBApiService';

const api = new JBApiService();

export default function GalleryScreen() {
    const [paintings, setPaintings] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadPaintings();
    }, []);

    const loadPaintings = async () => {
        const data = await api.getPaintings();
        setPaintings(data);
        setLoading(false);
    };

    const renderPainting = ({ item }) => (
        <View style={styles.card}>
            <Image source={{ uri: item.image }} style={styles.image} />
            <Text style={styles.name}>{item.name}</Text>
            <Text style={styles.price}>{item.price} €</Text>
        </View>
    );

    if (loading) {
        return <Text>Chargement...</Text>;
    }

    return (
        <FlatList
            data={paintings}
            renderItem={renderPainting}
            keyExtractor={item => item.id.toString()}
            numColumns={2}
        />
    );
}

const styles = StyleSheet.create({
    card: {
        flex: 1,
        margin: 10,
        backgroundColor: 'white',
        borderRadius: 12,
        padding: 10
    },
    image: {
        width: '100%',
        height: 200,
        borderRadius: 8
    },
    name: {
        fontSize: 16,
        fontWeight: 'bold',
        marginTop: 8
    },
    price: {
        fontSize: 14,
        color: '#1E3A8A',
        marginTop: 4
    }
});
```

---

**Ces exemples sont prêts à l'emploi ! Adaptez simplement les clés API et URLs selon votre environnement.**
