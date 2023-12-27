# Telegram Meme Bot


<h3 align="center"><a href="https://www.youtube.com/watch?v=99mFfEvAQO4">🎥Demo Video🎥</a></h3>

<h3 align="center"><a href="https://t.me/jetbrains_challenge_bot">🤖Try in Telegram (hosted on  a Raspberry Pi 4)🤖</a></h3>

## Project
Currently, when you are chatting with your friends and want to send a meme
you have to leave the messenger, go to an ad-filled app or website, generate the meme, download it
and then send it into the chat. But not anymore! This bot lets you generate meme right inside of Telegram!

Simply pick one of the shuffled images, enter your desired texts and forward the generated image!

## Features

- **Shuffle**: Creates an image where 3 random meme templates are resized to fit on one big image with any black space.
- **Select**: Pick one of the shuffled images, enter your texts and get the finished meme

## Dev Tools
<p align="center">
  <img src="https://logos-world.net/wp-content/uploads/2021/02/Docker-Logo-2015-2017.png" alt="Docker" width="562.5" height="421.875">

  
<img src="https://pre-commit.com/logo.svg" alt="Pre-Commit" width="400" height="400">
<img src="https://cdn.invicti.com/statics/img/drive/h2jfrvzrbyh1yff2n3wfu2hkqqps6x_uvqo.png" alt="MongoDB" width="500" height="250">
</p>

- **Docker**: To easily deploy and (in the future) scale the app, it is containerized using Docker and can be started
using docker-compose
- **pre-commit**: To ensure consistency in the codebase, pre-commit is used with: flake8, black, mypy
- **GitHub Actions**: To test the code at each commit, a GitHub actions pipeline was created that executes pre-commit
and runs all the tests

## Database
![img.png](https://upload.wikimedia.org/wikipedia/commons/9/93/MongoDB_Logo.svg)

For each meme template a document exists in the mongoDb collection. Since no relationships
exist in these objects, I decided to use a NoSQL database to avoid the overhead of using an SQL database such as Postgresql.

For each meme template, the x and y coordinates and the width and height of each
textbox where text can be entered is saved.

**Example document**


```json
{
  "id": "9",
  "name": "The Rock car meme",
  "text-locations": [
    {
      "x": 240,
      "y": 180,
      "width": 155,
      "height": 212
    },
    {
      "x": 414,
      "y": 183,
      "width": 160,
      "height": 211
    }
  ],
  "template-location": "./meme9.jpeg"
}
```

## Future Improvements
To make the bot more usable and scalable, some of the features listed here
could be implemented:

 <details>
  <summary>Add more meme templates</summary>

    Currently there are only 10 meme templates in the database.
    More templates should be added to give the user more options to choose from.
 </details>



 <details>
  <summary>Allow users to search for specific meme templates into microservices</summary>

    Currently the user has to call /shuffle until he finds a meme template that fits his needs.
    To avoid this, a feature could be added to let users search for specific templates
 </details>



 <details>
  <summary>Separate telegram interaction and image generator</summary>

    The part of the code that generates the code could be moved out into a separate
    docker container, to be able to scale it independetly without creating more instances of the
    container that interacts with the Telegram API.
 </details>

 <details>
  <summary>More Tests</summary>

    Tests for test ```ImageShuffler``` class have already been added. But
    of course more tests for the other classes could be added to improve the project
 </details>

 <details>
  <summary>Cloud Blob Storage</summary>

    Currently all the templates and created memes are saved on the host server, which adds
    additional workload on a single machine. To prevent this and use more storage, a cloud service
    such as AWS S3 Cloud Storage could be used to save the images in the cloud.
 </details>

## Outro
Thank you for making it this far and for taking my project into consideration.
If you have any more questions, don't hesitate to write me either via Slack or email:
 `hoppe.florian02@gmail.com`

Also if you want to learn more about me, feel free to check out my website
<h3 align="center">
  <a href="https://www.flohop.com/" target="_blank">💻Personal Website💻</a>
</h3>
