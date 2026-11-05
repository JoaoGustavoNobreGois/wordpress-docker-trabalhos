<?php
// Executado pelo WP-CLI depois da instalação inicial do WordPress.
$uploads = wp_upload_dir();
if (!empty($uploads['error'])) {
    WP_CLI::error($uploads['error']);
}

$target_dir = $uploads['basedir'] . '/locust';
wp_mkdir_p($target_dir);
$manifest = array();

$scenarios = array(
    'imagem-1mb' => array('title' => 'Cenário: imagem de 1 MB', 'image' => 'imagem-1mb.png'),
    'texto-400kb' => array('title' => 'Cenário: texto de 400 KB', 'text' => 'texto-400kb.txt'),
    'imagem-300kb' => array('title' => 'Cenário: imagem de 300 KB', 'image' => 'imagem-300kb.png'),
);

foreach ($scenarios as $slug => $scenario) {
    $content = '';
    $image_path = null;
    $image_bytes = null;
    $text_bytes = null;

    if (isset($scenario['image'])) {
        $source = '/mnt/generated/' . $scenario['image'];
        $destination = $target_dir . '/' . $scenario['image'];
        if (!copy($source, $destination)) {
            WP_CLI::error('Não foi possível copiar ' . $source);
        }
        $image_path = '/wp-content/uploads/locust/' . $scenario['image'];
        $image_bytes = filesize($destination);
        $content = '<p>Imagem usada no teste de carga.</p><img src="' . esc_url($image_path) . '" alt="Imagem do cenário">';
    } else {
        $text = file_get_contents('/mnt/generated/' . $scenario['text']);
        if ($text === false) {
            WP_CLI::error('Não foi possível ler o texto do cenário.');
        }
        $text_bytes = strlen($text);
        $content = '<p>' . esc_html($text) . '</p>';
    }

    $existing = get_page_by_path($slug, OBJECT, 'post');
    $post_data = array(
        'post_title' => $scenario['title'],
        'post_name' => $slug,
        'post_content' => $content,
        'post_status' => 'publish',
        'post_type' => 'post',
    );
    if ($existing) {
        $post_data['ID'] = $existing->ID;
    }
    $post_id = wp_insert_post($post_data, true);
    if (is_wp_error($post_id)) {
        WP_CLI::error($post_id->get_error_message());
    }

    $manifest[$slug] = array(
        'post_id' => $post_id,
        'image_path' => $image_path,
        'image_bytes' => $image_bytes,
        'text_bytes' => $text_bytes,
    );
}

$file = $target_dir . '/scenarios.json';
if (file_put_contents($file, wp_json_encode($manifest, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES)) === false) {
    WP_CLI::error('Não foi possível escrever o manifesto em ' . $file);
}
WP_CLI::success('Três publicações criadas/atualizadas: ' . $file);
