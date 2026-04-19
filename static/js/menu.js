// Espera o HTML carregar completamente antes de rodar o script
document.addEventListener('DOMContentLoaded', function() {
    const btnMenu = document.getElementById('btnMenu');
    const menuLateral = document.querySelector('.menu-lateral');
    const overlayMenu = document.getElementById('overlayMenu');

    // Função que liga/desliga as classes de abrir a gaveta
    function toggleMenu() {
        if (menuLateral) menuLateral.classList.toggle('aberto');
        if (overlayMenu) overlayMenu.classList.toggle('ativo');
    }

    // Ouve o clique no botão do hambúrguer
    if (btnMenu) {
        btnMenu.addEventListener('click', toggleMenu);
    }
    
    // Ouve o clique na parte escura (para fechar o menu clicando fora)
    if (overlayMenu) {
        overlayMenu.addEventListener('click', toggleMenu);
    }
});