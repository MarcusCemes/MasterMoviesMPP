<?php

if (session_status() == PHP_SESSION_NONE) {
    session_start();
}


$time = $_SERVER['REQUEST_TIME'];
$timeout_duration = 600;
if (isset($_SESSION['LAST_ACTIVITY']) && 
   ($time - $_SESSION['LAST_ACTIVITY']) > $timeout_duration) {
    session_unset();
    session_destroy();
    session_start();
}
$_SESSION['LAST_ACTIVITY'] = $time;



$authenticated = false;


if (isset($_SESSION['USER']) && isset($_SESSION['PASS'])) {
    
    
    $username = $_SESSION['USER'];
    $password = $_SESSION['PASS'];
    
    require_once('private/database_connection.php');
    
        
    $query = "SELECT userID,username,password FROM interface WHERE username = ?";

    $statement = $mysqli->prepare($query);
    $statement->bind_param("s", $username);
    $statement->execute();
    $statement->bind_result($r_userID, $r_user, $r_pass);

    if ($statement->fetch()) {
        
    if (password_verify($password, $r_pass)) {
        $authenticated = true;
         
        if (password_needs_rehash($r_pass, PASSWORD_DEFAULT)) {
            $newhash = password_hash($password, PASSWORD_DEFAULT);
            $updatestmt = $mysqli->prepare('UPDATE interface SET password = ? WHERE username = ?');
            $updatestmt->bind_param("ss", $newhash, $username);
            $updatestmt->execute();
            $updatestmt->close();
        }
    }
    
    $statement->close();
        
    }
}

$_SESSION['AUTHENTICATED'] = $authenticated;



?>
