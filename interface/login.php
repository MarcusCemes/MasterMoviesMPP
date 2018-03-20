<?php



if (isset($_REQUEST['USER']) && isset($_REQUEST['PASS'])) {
    
    if (session_status() == PHP_SESSION_NONE) {
        session_start();
    }
    
    $_SESSION['USER'] = $_REQUEST['USER'];
    $_SESSION['PASS'] = $_REQUEST['PASS'];
    
    require('private/authenticate.php');
    
    if ($_SESSION['AUTHENTICATED'] == true) {
        $response = array(
            'authenticated' => 1,
            'status' => 'Log-in successful'
        );
    } else {
        $response = array(
            'authenticated' => 0,
            'error' => 'Bad login'
        );
        
    }
    
    if (isset($mysqli)) $mysqli->close();
    
    
} else {
    $response = array(
        'authenticated' => 0,
        'error' => 'No login'
    );
}

echo json_encode($response);

?>