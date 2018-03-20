<?php


require('private/authenticate.php');

$response;

if ($_SESSION['AUTHENTICATED'] == true) {
    $response = array('authenticated'=>1);
} else {
    $response = array('authenticated'=>0);
}

echo json_encode($response);

?>